# Analisis y Mejora de Cobertura

Identificar brechas de cobertura y generar tests para cerrarlas.

## Agente: qa
## Skills: testing-guide.md, checklist-techstock.md

## Instrucciones
- Medir cobertura: `pytest --cov --cov-report=term-missing --tb=short -q`
- Identificar archivos con menor cobertura (priorizar routers/ y utils/)
- Priorizar brechas: critico (financieros) > alto (CRUD) > medio (validaciones) > bajo (lecturas)
- Generar tests siguiendo patron del proyecto (fixtures, local_id, assertions)
- Re-ejecutar cobertura y reportar antes vs despues — objetivo 95%+

## Argumentos
$ARGUMENTS
