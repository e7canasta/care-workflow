"""
Alarm Engine - Core logic for condition-based alarms with state machine.

Este módulo implementa el motor genérico de alarmas que puede ser usado
por múltiples blocks. Soporta:
- Condiciones arbitrarias con evaluación de verdad
- Hysteresis per-condition para evitar flapping
- State machine (IDLE → FIRING → COOLDOWN)
- Cooldown management
- Message templating

Filosofía: "Complejidad por Diseño"
- Motor centralizado, blocks específicos son wrappers
- State machine explícito
- Hysteresis aplicado a nivel de condición individual
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional


class AlarmState(str, Enum):
    """Estados del state machine de alarma."""

    IDLE = "idle"
    FIRING = "firing"
    COOLDOWN = "cooldown"


class ConditionWithHysteresis:
    """
    Representa una condición que puede tener hysteresis independiente.

    El hysteresis se aplica de manera diferente según la dirección de la condición:
    - Para condiciones ">" (mayor que): hysteresis resta del threshold
    - Para condiciones "<" (menor que): hysteresis suma al threshold
    - Para condiciones compuestas: cada sub-condición mantiene su hysteresis

    Attributes:
        evaluate_activation: Función que evalúa si la condición se ACTIVA
        evaluate_deactivation: Función que evalúa si la condición se DESACTIVA
        hysteresis: Valor de hysteresis para esta condición
        is_active: Estado actual de la condición (con hysteresis aplicado)
    """

    def __init__(
        self,
        evaluate_activation: Callable[[Dict[str, Any]], bool],
        evaluate_deactivation: Callable[[Dict[str, Any]], bool],
        hysteresis: float = 0.0,
    ):
        """
        Inicializa una condición con hysteresis.

        Args:
            evaluate_activation: Función que retorna True cuando condición se activa
            evaluate_deactivation: Función que retorna True cuando condición se desactiva
            hysteresis: Valor de hysteresis (aplicado en dirección opuesta)
        """
        self.evaluate_activation = evaluate_activation
        self.evaluate_deactivation = evaluate_deactivation
        self.hysteresis = hysteresis
        self.is_active = False

    def evaluate(self, params: Dict[str, Any]) -> bool:
        """
        Evalúa la condición aplicando hysteresis según estado actual.

        Args:
            params: Parámetros para evaluar la condición

        Returns:
            True si condición está activa (considerando hysteresis)
        """
        if not self.is_active:
            # Condición estaba inactiva, evaluar activación
            if self.evaluate_activation(params):
                self.is_active = True
                return True
            return False
        else:
            # Condición estaba activa, evaluar desactivación (con hysteresis)
            if self.evaluate_deactivation(params):
                self.is_active = False
                return False
            return True


class AlarmEngine:
    """
    Motor de alarmas genérico con state machine y hysteresis.

    Este engine centraliza la lógica de:
    - State machine (IDLE → FIRING → COOLDOWN)
    - Cooldown management
    - Evaluación de condiciones con hysteresis per-condition
    - Message templating

    Los blocks específicos (prediction_alarm, range_alarm, etc.) son wrappers
    que configuran este engine con condiciones pre-definidas.
    """

    def __init__(self):
        """Inicializa el engine con estado IDLE."""
        self._current_state: AlarmState = AlarmState.IDLE
        self._last_alarm_at: Optional[datetime] = None
        self._alarm_count: int = 0
        self._conditions: Dict[str, ConditionWithHysteresis] = {}

    def register_condition(self, name: str, condition: ConditionWithHysteresis):
        """
        Registra una condición con su hysteresis.

        Args:
            name: Nombre identificador de la condición
            condition: Condición con hysteresis configurado
        """
        self._conditions[name] = condition

    def evaluate(
        self,
        params: Dict[str, Any],
        combine_with: str = "AND",
        cooldown_seconds: float = 5.0,
        message_template: str = "Alarm triggered",
    ) -> Dict[str, Any]:
        """
        Evalúa todas las condiciones y actualiza state machine.

        Args:
            params: Parámetros para evaluar las condiciones
            combine_with: "AND" o "OR" para combinar múltiples condiciones
            cooldown_seconds: Segundos mínimos entre alarmas
            message_template: Template de mensaje con placeholders

        Returns:
            Dict con alarm_active, alarm_message, state, alarm_count
        """
        current_time = datetime.now()

        # Evaluar todas las condiciones
        condition_results = {
            name: cond.evaluate(params) for name, cond in self._conditions.items()
        }

        # Combinar resultados según operador
        if combine_with == "AND":
            all_conditions_met = all(condition_results.values())
        elif combine_with == "OR":
            all_conditions_met = any(condition_results.values())
        else:
            raise ValueError(f"Invalid combine_with: {combine_with}. Use 'AND' or 'OR'")

        # Check si cooldown ha expirado
        cooldown_elapsed = True
        if self._last_alarm_at is not None:
            time_since_last = (current_time - self._last_alarm_at).total_seconds()
            cooldown_elapsed = time_since_last >= cooldown_seconds

        # State machine logic
        alarm_active = False
        alarm_message = ""

        if self._current_state == AlarmState.IDLE:
            # Transición: IDLE → FIRING
            if all_conditions_met and cooldown_elapsed:
                self._current_state = AlarmState.FIRING
                self._last_alarm_at = current_time
                self._alarm_count += 1
                alarm_active = True
                alarm_message = message_template.format(**params)

        elif self._current_state == AlarmState.FIRING:
            # Stay in FIRING (alarm permanece activo)
            alarm_active = True
            alarm_message = message_template.format(**params)
            # Transición: FIRING → COOLDOWN
            self._current_state = AlarmState.COOLDOWN

        elif self._current_state == AlarmState.COOLDOWN:
            # Transición: COOLDOWN → IDLE
            if not all_conditions_met:
                # Condiciones ya no se cumplen, volver a IDLE
                self._current_state = AlarmState.IDLE
            elif cooldown_elapsed:
                # Cooldown expiró, verificar si re-disparar
                if all_conditions_met:
                    self._current_state = AlarmState.FIRING
                    self._last_alarm_at = current_time
                    self._alarm_count += 1
                    alarm_active = True
                    alarm_message = message_template.format(**params)
                else:
                    self._current_state = AlarmState.IDLE

        return {
            "alarm_active": alarm_active,
            "alarm_message": alarm_message,
            "state": self._current_state.value,
            "alarm_count": self._alarm_count,
            "condition_states": condition_results,  # Para debugging
        }

    def reset(self):
        """Reset del engine (útil para testing)."""
        self._current_state = AlarmState.IDLE
        self._last_alarm_at = None
        self._alarm_count = 0
        for condition in self._conditions.values():
            condition.is_active = False


def create_threshold_condition(
    param_name: str, threshold: float, hysteresis: float, direction: str = "above"
) -> ConditionWithHysteresis:
    """
    Factory para crear condiciones de threshold simples.

    Args:
        param_name: Nombre del parámetro a evaluar
        threshold: Valor de threshold
        hysteresis: Valor de hysteresis
        direction: "above" (>=) o "below" (<)

    Returns:
        ConditionWithHysteresis configurada
    """
    if direction == "above":
        # Activar: value >= threshold
        # Desactivar: value < (threshold - hysteresis)
        return ConditionWithHysteresis(
            evaluate_activation=lambda params: params[param_name] >= threshold,
            evaluate_deactivation=lambda params: params[param_name]
            < (threshold - hysteresis),
            hysteresis=hysteresis,
        )
    elif direction == "below":
        # Activar: value < threshold
        # Desactivar: value >= (threshold + hysteresis)
        return ConditionWithHysteresis(
            evaluate_activation=lambda params: params[param_name] < threshold,
            evaluate_deactivation=lambda params: params[param_name]
            >= (threshold + hysteresis),
            hysteresis=hysteresis,
        )
    else:
        raise ValueError(f"Invalid direction: {direction}. Use 'above' or 'below'")


def create_range_condition(
    param_name: str, min_threshold: float, max_threshold: float, hysteresis: float
) -> ConditionWithHysteresis:
    """
    Factory para crear condiciones de rango.

    Args:
        param_name: Nombre del parámetro a evaluar
        min_threshold: Threshold inferior
        max_threshold: Threshold superior
        hysteresis: Hysteresis aplicado a ambos lados

    Returns:
        ConditionWithHysteresis configurada para rango
    """
    # Activar: value < min_threshold OR value > max_threshold
    # Desactivar: value >= (min_threshold + hysteresis) AND value <= (max_threshold - hysteresis)
    return ConditionWithHysteresis(
        evaluate_activation=lambda params: params[param_name] < min_threshold
        or params[param_name] > max_threshold,
        evaluate_deactivation=lambda params: params[param_name]
        >= (min_threshold + hysteresis)
        and params[param_name] <= (max_threshold - hysteresis),
        hysteresis=hysteresis,
    )
