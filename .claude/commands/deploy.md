# Preparar Deploy

Verificar que el proyecto esta listo para desplegar.

## Agente: ops
## Skills: build-deploy.md, checklist-techstock.md

## Instrucciones
- Ejecutar `pytest --tb=short -q` — todos deben pasar
- Verificar: no secrets en git, requirements.txt actualizado, migraciones al dia
- Si Docker: verificar docker-compose.yml y Dockerfile
- Si Windows: ejecutar /build para generar .exe
- Presentar checklist final: tests, cobertura, CSRF, audit, secrets, build

## Argumentos
$ARGUMENTS
