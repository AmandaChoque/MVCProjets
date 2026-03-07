# TODO - Client List Search and Filter

## Plan - COMPLETED

### 1. Update `projects/views.py`

- [x] Modified the `clientes` view to handle:
  - Search by NIT/CI (`search_nit_ci`)
  - Search by Nombre/Apellido (`search_nombre`) - searches in nombre, apellido_paterno, apellido_materno
  - Filter by tipo_contratante (`filter_tipo`)

### 2. Update `projects/templates/clientes.html`

- [x] Add search input field for Nombre/Apellido
- [x] Add search input field for NIT/CI
- [x] Add dropdown filter for tipo_contratante
- [x] Add Apply/Clear buttons for the filters
- [x] Pass the filter values back to the template for display

## Summary

- Added Nombre/Apellido search functionality using Q objects (OR search)
- Added NIT/CI search functionality using `nit_ci__icontains` filter
- Added tipo_contratante filter dropdown with options: Empresa, Personal, Entidad Pública
- Added "Buscar" (Search) and "Limpiar" (Clear) buttons
- Filter values are preserved in the form after submission
- All filters work together (can combine name + NIT/CI + tipo)
