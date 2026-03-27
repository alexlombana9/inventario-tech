# Skill: Preparar Deploy

Verifica que el proyecto esta listo para desplegar.

## Instrucciones

### 1. Verificaciones pre-deploy
- Ejecuta `pytest --tb=short -q` — todos deben pasar
- Verifica que no hay archivos .env o credenciales en git: `git status`
- Verifica que requirements.txt esta actualizado
- Verifica que migrations.py tiene todas las migraciones necesarias

### 2. Docker (si aplica)
- Verifica que docker-compose.yml esta actualizado
- Verifica que el Dockerfile funciona: `docker-compose build`

### 3. Instalador Windows (si aplica)
- Ejecuta /build para generar el .exe
- Verifica que launcher.py funciona standalone

### 4. Checklist final
Presenta una checklist con:
- [ ] Tests: X/X passed
- [ ] Cobertura: X%
- [ ] Migraciones: actualizadas
- [ ] CSRF: en todos los formularios
- [ ] Audit: en todas las mutaciones
- [ ] Secrets: no expuestos
- [ ] Build: exitoso

## Tipo de deploy
$ARGUMENTS
