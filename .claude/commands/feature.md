# Implementar Feature

Flujo completo para implementar una nueva funcionalidad en TechStock.

## Agente: developer
## Skills: crud-pattern.md, checklist-techstock.md

## Instrucciones
- Analizar el pedido y leer codigo relacionado para entender el contexto
- Presentar plan al usuario antes de implementar (archivos a crear/modificar)
- Implementar en orden: modelo → migracion → router → templates → sidebar/auth/main
- Seguir el patron CRUD estandar del proyecto (ver skills/crud-pattern.md)
- Crear tests en tests/test_<modulo>.py con fixtures de conftest.py
- Ejecutar `pytest --tb=short -q` y verificar 100% verde
- Validar checklist: CSRF, log_audit, soft delete, local_id, PRG 303

## Argumentos
$ARGUMENTS
