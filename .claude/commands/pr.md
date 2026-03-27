# Skill: Crear Pull Request

Prepara y crea un Pull Request profesional con validaciones previas.

## Instrucciones

### 1. Validar cambios
- `git status` — verificar que hay cambios para commitear o ya commiteados
- `git diff --stat` — resumen de archivos modificados
- `pytest --tb=short -q` — TODOS los tests deben pasar. Si fallan, PARAR

### 2. Analizar scope
- `git log main..HEAD --oneline` — ver commits en la rama actual
- Si estamos en main, crear rama nueva: `git checkout -b <tipo>/<descripcion-corta>`
  - Tipos: `feat/`, `fix/`, `refactor/`, `perf/`, `docs/`, `test/`, `chore/`
- Categorizar el cambio: feature, bugfix, refactor, perf, docs, test, chore

### 3. Commit pendientes
Si hay cambios sin commitear:
- Agrupar cambios logicos en commits separados si tiene sentido
- Mensajes de commit en espanol, descriptivos, formato convencional:
  - `feat: descripcion de la nueva funcionalidad`
  - `fix: descripcion del bug corregido`
  - `refactor: descripcion del refactor`
  - `test: descripcion de tests agregados`
  - `perf: descripcion de la optimizacion`

### 4. Push y crear PR
```bash
git push -u origin <rama>
gh pr create --title "<titulo>" --body "$(cat <<'EOF'
## Resumen
<descripcion clara de los cambios y su motivacion>

## Cambios
- <lista de cambios principales>

## Tests
- [ ] Tests existentes pasan (pytest)
- [ ] Tests nuevos agregados para cambios
- [ ] Cobertura mantenida o mejorada

## Checklist
- [ ] CSRF en formularios POST nuevos
- [ ] log_audit() en mutaciones nuevas
- [ ] Soft delete (no db.delete())
- [ ] Filtro local_id en queries nuevas
- [ ] Convenciones CLAUDE.md respetadas

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 5. Reporte
- URL del PR creado
- Resumen de cambios incluidos
- Validaciones pasadas

## Contexto del PR
$ARGUMENTS
