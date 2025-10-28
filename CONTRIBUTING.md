# Contribuir a Care Workflow

¡Gracias por tu interés en contribuir a Care Workflow! Este documento proporciona las pautas para contribuir al proyecto.

## 🚀 Configuración del entorno de desarrollo

1. **Fork y clona el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/care-workflow.git
   cd care-workflow
   ```

2. **Configura el entorno virtual**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. **Instala las dependencias de desarrollo**
   ```bash
   pip install -e ".[dev]"
   ```

## 🧪 Ejecutar tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests con cobertura
pytest --cov=care_workflow --cov-report=html

# Ejecutar tests específicos
pytest tests/test_core.py -v
```

## 🎨 Estándares de código

Este proyecto usa herramientas de formateo y linting automático:

```bash
# Formatear código
black .

# Revisar estilo de código
ruff check .

# Aplicar correcciones automáticas
ruff check . --fix
```

## 📝 Tipos de contribuciones

### 🐛 Reportar bugs
- Usa el template de issue para bugs
- Incluye pasos para reproducir el problema
- Proporciona información del sistema y versión de Python

### ✨ Solicitar nuevas características
- Usa el template de issue para features
- Describe claramente el caso de uso
- Considera proporcionar una implementación

### 🔧 Contribuir código

1. **Crea una rama para tu feature**
   ```bash
   git checkout -b feature/nombre-descriptivo
   ```

2. **Haz tus cambios**
   - Sigue las convenciones de naming existentes
   - Agrega tests para nueva funcionalidad
   - Actualiza documentación si es necesario

3. **Asegúrate de que todo funcione**
   ```bash
   # Tests
   pytest
   
   # Linting
   ruff check .
   black --check .
   ```

4. **Commit tus cambios**
   ```bash
   git commit -m "✨ feat: descripción clara del cambio"
   ```

5. **Push y crea un Pull Request**
   ```bash
   git push origin feature/nombre-descriptivo
   ```

## 📋 Convenciones de commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - Nueva característica
- `fix:` - Corrección de bug
- `docs:` - Cambios en documentación
- `style:` - Cambios de formato (no afectan funcionalidad)
- `refactor:` - Refactoring de código
- `test:` - Agregar o corregir tests
- `chore:` - Tareas de mantenimiento

Ejemplos:
```
✨ feat: agregar soporte para workflows anidados
🐛 fix: corregir validación de estados de workflow
📚 docs: actualizar README con nuevos ejemplos
🧪 test: agregar tests para WorkflowStep
```

## 🏗️ Estructura del proyecto

```
care-workflow/
├── care_workflow/          # Código fuente principal
│   ├── __init__.py
│   └── core.py
├── tests/                  # Tests unitarios
│   ├── __init__.py
│   └── test_core.py
├── examples/               # Ejemplos de uso
│   └── basic_workflow.py
├── docs/                   # Documentación (futuro)
├── .github/                # GitHub Actions y templates
│   └── workflows/
│       └── ci.yml
├── main.py                 # Punto de entrada
├── pyproject.toml          # Configuración del proyecto
└── README.md
```

## 🔍 Revisión de código

Todos los Pull Requests deben:

- ✅ Pasar todos los tests
- ✅ Mantener o mejorar la cobertura de tests
- ✅ Seguir las convenciones de código
- ✅ Incluir documentación si es necesario
- ✅ Tener una descripción clara del cambio

## 📞 ¿Necesitas ayuda?

- 💬 Abre un issue con la etiqueta `question`
- 📧 Contacta a los mantenedores: care@visiona.app

## 📄 Código de conducta

Este proyecto se adhiere al Contributor Covenant Code of Conduct. Al participar, se espera que mantengas este código.

---

¡Gracias por hacer que Care Workflow sea mejor! 🎉