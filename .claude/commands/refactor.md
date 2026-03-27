# Skill: Refactorizar Codigo

Reestructura codigo existente de forma segura, sin cambiar comportamiento.

## Instrucciones

### 1. Analisis de impacto
- Lee CLAUDE.md para entender convenciones
- Usa agente Explore para mapear todas las dependencias del codigo objetivo
- Identifica todos los archivos que importan/usan el codigo a refactorizar
- Identifica tests existentes que cubren el codigo

### 2. Validar cobertura pre-refactor
- Ejecuta `pytest --tb=short -q` — confirma que todo pasa ANTES de tocar nada
- Si hay tests fallando, PARA y reporta. No refactorices sobre una base rota

### 3. Plan de refactor
Presenta al usuario:
- **Que cambia**: archivos y funciones afectadas
- **Que NO cambia**: comportamiento externo, API publica, rutas
- **Riesgo**: bajo/medio/alto segun cantidad de dependencias
- **Estrategia**: renombrar, extraer, mover, simplificar, o combinar

### 4. Ejecutar refactor
- Aplica cambios en orden de dependencias (hojas primero, raiz al final)
- Actualiza TODOS los imports y referencias
- Mantiene convenciones del proyecto (espanol, patron CRUD, etc.)
- NO agrega funcionalidad nueva — solo reestructura

### 5. Verificacion
- Ejecuta `pytest --tb=short -q` — misma cantidad de tests, todos verdes
- Verifica que no hay imports rotos: `python -c "from main import app"`
- Si algun test falla, revierte el cambio que lo rompio y ajusta

## Codigo a refactorizar
$ARGUMENTS
