# Guía de Contribución

¡Gracias por tu interés en contribuir a BOT360!

## 📋 Código de Conducta

Este proyecto adhiere a un código de conducta que todos los contribuidores deben respetar:
- Sé respetuoso con los demás
- Reporta problemas de forma clara y constructiva
- Colabora de buena fe

## 🚀 Cómo Contribuir

### Reportar Bugs

1. Verificar que el bug no está [ya reportado](https://github.com/tu-usuario/bot360/issues)
2. Crear un nuevo issue con:
   - **Título claro** describiendo el problema
   - **Descripción detallada**
   - **Pasos para reproducir**
   - **Comportamiento esperado vs actual**
   - **Entorno**: Windows version, Python version, navegador

### Sugerir Mejoras

1. Crear un issue con etiqueta `enhancement`
2. Describir la mejora propuesta
3. Explicar casos de uso

### Pull Requests

1. **Fork** el repositorio
2. Crear una rama para tu feature:
   ```bash
   git checkout -b feature/descripcion-clara
   ```
3. Hacer commits atómicos con mensajes claros:
   ```bash
   git commit -m "Agregar funcionalidad X que resuelve #123"
   ```
4. Push a tu rama:
   ```bash
   git push origin feature/descripcion-clara
   ```
5. Abrir Pull Request con descripción clara

## 📐 Estándares de Código

### Python Style Guide (PEP 8)

```bash
# Formatear código
black src/ tests/

# Linter
flake8 src/ tests/

# Type checking
mypy src/
```

### Commits

Usar formato convencional:
```
<tipo>(<alcance>): <descripción>

<cuerpo>

Fixes #<issue>
```

**Tipos**:
- `feat`: Nueva característica
- `fix`: Corrección de bug
- `docs`: Documentación
- `style`: Formato de código
- `refactor`: Refactorización
- `test`: Pruebas
- `chore`: Cambios en build/dependencies

### Ejemplo:
```
feat(automation): mejorar validación de selectores XPath

- Agregar validación en tiempo real
- Mejorar mensajes de error
- Agregar pruebas unitarias

Fixes #42
```

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Cobertura
pytest --cov=src

# Test específico
pytest tests/test_bot.py::test_login
```

- Cobertura mínima: 70%
- Tests para nuevas características

## 📝 Documentación

- Docstrings en español/inglés
- Mantener README.md actualizado
- Actualizar CHANGELOG.md

### Formato de Docstring:
```python
def tu_funcion(parametro):
    """
    Descripción breve de la función.
    
    Descripción larga explicando:
    - Qué hace
    - Por qué es importante
    - Casos especiales
    
    Args:
        parametro (type): Descripción del parámetro
        
    Returns:
        type: Descripción del retorno
        
    Raises:
        Exception: Qué excepciones puede lanzar
        
    Example:
        >>> resultado = tu_funcion("ejemplo")
        >>> print(resultado)
    """
```

## 🔐 Seguridad

- **NUNCA** commitear credenciales o secrets
- Usar `.env` para configuración sensible
- Validar input del usuario
- Reportar vulnerabilidades a: security@bot360.local

## 📦 Instalación para Desarrollo

```bash
# Clonar repo
git clone https://github.com/tu-usuario/bot360.git
cd bot360

# Entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar en modo desarrollo
pip install -e ".[dev]"

# Pre-commit hooks (opcional)
pip install pre-commit
pre-commit install
```

## 🔄 Proceso de Review

1. Tu PR será revisada por mantendores
2. Se pedirán cambios si es necesario
3. Después de aprobación, será mergeada
4. Tu código será incluido en la siguiente release

## 📊 Labels en Issues

- 🐛 `bug`: Problema a corregir
- ✨ `enhancement`: Mejora o nueva característica
- 📖 `documentation`: Mejoras en docs
- 🆘 `help wanted`: Ayuda buscada
- ❓ `question`: Preguntas
- 🔒 `security`: Problemas de seguridad

## 🏆 Créditos

Todos los contribuidores serán mencionados en:
- README.md
- Releases notes
- Página de contributors en GitHub

---

**¡Gracias por ayudar a mejorar BOT360!** 🙏

