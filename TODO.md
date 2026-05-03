# UWE Diagrams TODO

## Plan:

- **Info Gathered:** Models from empleados/projects/inventario (Empleado, Proyecto, Cliente, ContratoProyecto, PagoProyecto, Sede, TareaChecklist, Proveedor, Insumo, etc.). Existing class/nav diagrams.
- **Goal:** Code to generate UWE diagrams (Use Case, Sequence, Activity).
- **Files:** uwe_generator.py (parses models → Mermaid), \*.mmd files.

## Steps:

- [x] 1. Create TODO.md (tracking)
- [x] 2. Create uwe_generator.py
- [x] 3. Generate use_case.mmd
- [x] 4. Generate sequence_create_project.mmd
- [x] 5. Generate sequence_jornada.mmd
- [x] 6. Generate activity_project_lifecycle.mmd
- [x] 7. Update existing diagrams if needed (N/A)
- [x] 8. Test Mermaid render (via browser or tool) - \*.mmd ready for mermaid.live
- [x] 9. Complete

**Run:** python uwe_generator.py to generate all.
