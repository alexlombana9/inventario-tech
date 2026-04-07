# Workflow de Pull Request — TechStock

## Ramas
- `feat/<descripcion>` — nueva funcionalidad
- `fix/<descripcion>` — correccion de bug
- `refactor/<descripcion>` — reestructuracion sin cambio de comportamiento
- `perf/<descripcion>` — optimizacion de rendimiento
- `test/<descripcion>` — solo tests
- `docs/<descripcion>` — solo documentacion
- `chore/<descripcion>` — mantenimiento, dependencias, CI

## Commits
Formato en espanol, convencional:
```
feat: agregar modulo de notificaciones
fix: corregir calculo de ganancia en ventas anuladas
refactor: extraer logica de pago a utils/financial.py
test: agregar tests para locales router
perf: agregar joinedload en dashboard queries
```

## Template de PR
```bash
gh pr create --title "feat: descripcion corta" --body "$(cat <<'EOF'
## Resumen
- Que se hizo y por que

## Cambios
- Lista de archivos/modulos modificados y naturaleza del cambio

## Tests
- [ ] Tests nuevos agregados
- [ ] Suite completa pasa (`pytest --tb=short -q`)
- [ ] Cobertura no disminuye

## Checklist
- [ ] CSRF en todos los forms POST
- [ ] log_audit en todas las mutaciones
- [ ] Filtro local_id en todas las queries
- [ ] Soft delete (nunca db.delete)
- [ ] PRG en todos los POST (redirect 303)
EOF
)"
```

## Pre-PR Validacion
1. `pytest --tb=short -q` — todos los tests pasan
2. `git diff main...HEAD` — revisar todos los cambios
3. Sin archivos sensibles (.env, .secret_key, credentials)
4. Commit messages siguen formato convencional
