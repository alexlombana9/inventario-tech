# Build del Instalador

Construir el instalador .exe de TechStock (PyInstaller + Inno Setup).

## Agente: ops
## Skills: build-deploy.md

## Instrucciones
- Verificar pre-requisitos: PyInstaller (`pip show pyinstaller`) e Inno Setup (`ISCC.exe`)
- Ejecutar `pytest --tb=short -q` — abortar si hay fallos
- Build: `pyinstaller techstock.spec --clean --noconfirm`
- Installer: `ISCC.exe installer/techstock.iss`
- Si argumento es "clean": eliminar dist/, build/ antes de construir
- Reportar ubicacion y tamano del .exe generado

## Argumentos
$ARGUMENTS
