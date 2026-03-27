# Skill: Build del Instalador

Construye el instalador .exe de TechStock.

## Instrucciones

### Pre-requisitos
Verifica que esten instalados:
- PyInstaller: `pip show pyinstaller`
- Inno Setup: buscar `ISCC.exe` en `C:\Program Files*\Inno Setup*\`

Si falta alguno, informa al usuario como instalarlo.

### Proceso de Build

1. **Tests primero**: ejecuta `pytest --tb=short -q` y aborta si hay fallos
2. **PyInstaller**: ejecuta `pyinstaller techstock.spec --clean --noconfirm`
3. **Verificar output**: verifica que `dist/TechStock/` contiene los archivos esperados
4. **Inno Setup**: ejecuta `ISCC.exe installer/techstock.iss`
5. **Resultado**: informa la ubicacion del .exe generado y su tamano

### Si el argumento es "clean"
Limpia builds anteriores: elimina `dist/`, `build/`, `*.spec` cache.

## Argumento
$ARGUMENTS
