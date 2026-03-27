# Skill: Corregir Bug

Flujo profesional para diagnosticar y corregir bugs en TechStock.

## Instrucciones

### 1. Diagnostico
- Usa agente Explore para encontrar la causa raiz
- Lee los archivos relevantes completos (no solo fragmentos)
- Identifica si el bug es de: logica, SQL, template, auth, o frontend

### 2. Test primero (TDD)
- Escribe un test que reproduzca el bug ANTES de corregirlo
- El test debe fallar al ejecutarse (confirma que el bug existe)

### 3. Fix minimo
- Corrige SOLO el codigo necesario, sin refactors innecesarios
- Sigue las convenciones del proyecto (ver CLAUDE.md)
- Si el fix toca POST routes: verificar CSRF token
- Si el fix toca datos: verificar audit logging

### 4. Verificacion
- Ejecuta `pytest` completo
- Verifica que el test nuevo pasa
- Verifica que no se rompieron otros tests

## Bug reportado
$ARGUMENTS
