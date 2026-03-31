# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Empresa y Propósito del Sistema

**SOBOTEC S.R.L.** es una empresa boliviana dedicada a la **instalación, ampliación y mantenimiento de sistemas de seguridad** (cámaras IP/analógicas, DVR/NVR, alarmas y sensores).

Este sistema web gestiona el ciclo completo de un proyecto de seguridad:
1. **Captación**: Se registra un cliente y se vincula a un proyecto.
2. **Proyecto**: Se crea el proyecto, se asigna un equipo de empleados y se controla su estado (pendiente → en progreso → completado).
3. **Sedes**: Cada proyecto puede tener múltiples sedes (puntos de instalación) con checklist de tareas y fotos.
4. **Contratos**: Modelo unificado `Contrato` con `tipo='empleado'` o `tipo='proyecto'`. Los empleados tienen jornadas diarias registradas.
5. **Inventario y compras**: Insumos/equipos catalogados. Stock calculado automáticamente por señales (FIFO). Se registra qué insumos requiere cada proyecto (`Requiere`) y qué compras se realizan a proveedores (`Compra`).
6. **Pagos**: Pagos del cliente al proyecto (`Pago`) y de la empresa al empleado (`PagoEmpleado`). Señal Django actualiza `estado_pago` del proyecto.
7. **Reportes**: PDF y gráficos de análisis para proyectos, pagos e inventario.

El sistema es de uso interno, con autenticación y sesión con timeout de 30 minutos.

## Stack
- **Backend**: Django 5.1.2 (Python), SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Bootstrap 5.3 + Bootstrap Icons + HTML templates
- **PDF**: xhtml2pdf (pisa), reportlab
- **Charts**: matplotlib (base64 encoded PNG)
- **Server**: Gunicorn + WhiteNoise
- **Venv**: `venv/` (Windows)

## Development Commands
```bash
# Activate venv (Windows)
venv\Scripts\activate

# Run dev server
python manage.py runserver

# After model changes
python manage.py makemigrations --name="description_of_change"
python manage.py migrate

# Check for errors
python manage.py check

# Run all tests
python manage.py test projects

# Run a single test class
python manage.py test projects.tests.PaymentFormCleanMontoTest

# Run a single test method
python manage.py test projects.tests.PaymentFormCleanMontoTest.test_monto_entero_valido
```

## Architecture — Three Django Apps

URL routing: `project_management/urls.py` is the root; it `include()`s `inventario.urls` and `pagos.urls`.

### `projects/` — Core app
- `models.py` — all core models (see below)
- `views.py` — all project/employee/contrato/sede/notificacion views (~1864 lines, function-based)
- `form.py` — all forms (NOT `forms.py`)
- `decorators.py` — `@cargo_required(*cargos)` for role-based access
- `context_processors.py` — injects `user_cargo`, `es_admin`, `es_admin_o_gerente`, `es_admin_sec`, `es_campo` into every template
- `migrations/` — 18 migrations (0001–0018)
- `templates/` — all HTML templates (~50+ files), extend `base.html` in `templates/`

### `inventario/` — Inventory app
- `models.py` — Proveedor, Insumo, Requiere, Compra, RequiereLote
- `views.py`, `urls.py`, `forms.py`, `signals.py`
- Stock recalculated automatically via `post_save`/`post_delete` signals on Compra/Requiere

### `pagos/` — Payments app
- `models.py` — PagoBase (abstract), Pago (cliente→proyecto), PagoEmpleado (empresa→empleado)
- `views.py`, `urls.py`, `forms.py`
- `post_save`/`post_delete` on `Pago` triggers `proyecto._sync_estado_pago()`

## Models Summary

### `projects/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `AuditModel` | created, updated_at, deleted_at, deleted_by, activo | Abstract base for all models |
| `Cliente` | nit_ci, nombre, apellido_paterno, apellido_materno, cargo, tipo_contratante, telefono, correo, direccion, nombre_entidad, representante_legal, activo | Soft-delete via `delete()`. `ActiveClienteManager` (default, activo=True), `all_objects`. `nombre_entidad`/`representante_legal` only for tipo_contratante='entidad_publica' |
| `Empleado` | nombre, apellido_paterno, apellido_materno, cargo, carnet_identidad (unique), numero_celular, is_active | **Extends `AbstractUser` directly** (not OneToOne). cargo choices: administrador/gerente/instalador/tecnico_soporte/secretaria |
| `Proyecto` | codigo, nombre, descripcion, estado_proyecto, tipo_proyecto, fecha_inicio, fecha_fin, observacion, estado_pago, monto_total, FK→Cliente/creado_por, M2M→Empleado(equipo) | `_sync_estado_pago()` called by pagos signals. `equipo` is M2M for the team |
| `HistorialPresupuesto` | monto_anterior, monto_actual, motivo_cambio, FK→Proyecto | Auto-created by pre_save signal on Proyecto when monto_total changes |
| `Progreso` | proyecto, fecha, porcentaje (0-100), descripcion, observacion | Cannot decrease porcentaje (enforced in form) |
| `Contrato` | tipo ('empleado'/'proyecto'), tipo_salario, FK→Proyecto, FK→Empleado, fecha_firma, fecha_inicio, fecha_fin, monto_acordado, observaciones, documento | **Unified model** replacing old ContratoEmpleado + ContratoProyecto. `monto_diario` property. UniqueConstraints: one active per empleado, one active per proyecto |
| `JornadaEmpleado` | FK→Contrato, FK→Proyecto, fecha, dias (0.5 or 1.0), observacion | Daily work log. `monto` property = dias × contrato.monto_diario |
| `Sede` | FK→Proyecto, nombre, direccion, descripcion, latitud, longitud, estado | Installation point within a project. `porcentaje_checklist` and `_sync_estado()` based on TareaChecklist |
| `FotoSede` | FK→Sede, foto (ImageField), descripcion, FK→subida_por | upload_to='sedes/fotos/' |
| `TareaChecklist` | FK→Sede, descripcion, orden, completado, fecha_completado, FK→completado_por | Triggers `sede._sync_estado()` via signal |
| `Notificacion` | FK→destinatario(User), tipo, mensaje, leida, FK→Proyecto, FK→Sede, fecha | Internal notifications. Types: sede_completada/tarea_completada/general |

### `inventario/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `Proveedor` | nombre, rubro, nit (unique when not blank), telefono, correo, direccion, encargado_* fields | db_table='inventario_proveedor' |
| `Insumo` | nombre, marca, modelo, categoria, ultimo_precio_compra, stock, stock_minimo | `stock` and `ultimo_precio_compra` maintained by signals — never modify directly. `stock_status` property → 'agotado'/'bajo'/'ok' |
| `Requiere` | FK→Proyecto, FK→Insumo, cantidad, costo_unitario | `unique_together (proyecto, insumo)`. `subtotal` property. Price copied at assignment |
| `Compra` | FK→Proveedor, FK→Insumo, cantidad, costo_unitario, costo_total, fecha | Replaces old `Realizar`. Triggers stock recalculation via signal |
| `RequiereLote` | FK→Requiere, FK→Compra, cantidad | Links project requirements to purchase lots (FIFO tracking) |

### `pagos/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `PagoBase` | monto, fecha, tipo_pago (efectivo/transferencia) | Abstract base |
| `Pago` | FK→Proyecto, numero_referencia | db_table='projects_pago'. Post-save/delete → `proyecto._sync_estado_pago()` |
| `PagoEmpleado` | FK→Contrato, concepto (pago_jornada/adelanto/liquidacion/dia_extra/otro) | db_table='projects_pagoempleado'. UniqueConstraint: one active liquidacion per contrato |

## Key Patterns

**Soft-delete**: Set `activo=False`. `Cliente` overrides `delete()`. All other models: `deactivate_*` views set `activo=False` directly. Hard delete (`project_delete`) is the exception, only for projects.

**Forms**: All forms use Bootstrap `form-control`/`form-select` widgets. Decimal fields (monto, costo_unitario) use `CharField` + `clean_*` with regex `r'\d+(\.\d{1,2})?'` — no commas, dot as decimal separator. Forms live in `form.py` (projects) or `forms.py` (inventario, pagos).

**Views**: All use `@login_required`. Pattern: GET returns form, POST validates and redirects. Use `messages.success()` on create/update. Use `get_object_or_404()`.

**Role-based access**: `@cargo_required(*cargos)` from `decorators.py` after `@login_required`. Predefined groups: `ROLES_ADMIN = ('administrador', 'gerente')`, `ROLES_ADMIN_SEC` (adds secretaria), `ROLES_CAMPO` (adds instalador, tecnico_soporte). Superusers bypass all checks. Templates use `{% if es_admin %}` / `{% if es_campo %}` etc.

**Empleado is the User model**: `AUTH_USER_MODEL = 'projects.Empleado'`. Access the current user's cargo via `request.user.cargo` (not `request.user.employee_profile.cargo`).

**Pagination**: `Paginator` with configurable `per_page` (10/20/50/100) via GET param.

**PDF export**: `?pdf` renders inline, `?pdf&download` forces download. Uses `xhtml2pdf.pisa.CreatePDF`.

**Stock management**: `Insumo.stock` is a denormalized field maintained exclusively by signals in `inventario/signals.py`. Never modify directly from views. Same for `ultimo_precio_compra`.

## URL Structure

```
/                                            → landing
/dashboard/                                  → home
/signin/, /signup/, /signout/                → auth
/extend-session/                             → AJAX session extension (POST)
/cambiar-contrasena/                         → change password
/mi-trabajo/                                 → instalador dashboard

/projects/                                   → list + filters
/projects/create/
/projects/<id>/                              → detail/edit
/projects/<id>/view/                         → full aggregated view
/projects/<id>/complete/
/projects/<id>/delete/                       → hard delete
/projects/<id>/deactivate/
/projects/<id>/progreso/nuevo/
/progreso/<id>/
/progreso/<id>/eliminar/

# Sedes de instalación
/projects/<id>/sedes/nueva/
/sedes/<id>/                                 → edit
/sedes/<id>/ver/                             → view (checklist, fotos)
/sedes/<id>/deactivate/
/sedes/<id>/tareas/nueva/
/tareas/<id>/toggle/
/tareas/<id>/eliminar/
/sedes/<id>/fotos/subir/
/fotos/<id>/eliminar/

# Equipo del proyecto
/projects/<id>/equipo/agregar/
/projects/<id>/equipo/<id_employee>/remover/

# Contratos
/projects/<id>/contrato-proyecto/nuevo/
/contratos/proyecto/<id>/
/contratos/proyecto/<id>/deactivate/
/contratos/empleado/<id>/
/contratos/empleado/<id>/deactivate/
/employees/<id>/contratos/nuevo/             → create contrato from employee profile

# Jornadas
/contratos/empleado/<id>/jornadas/nueva/
/jornadas/<id>/
/jornadas/<id>/eliminar/

/employees/                                  → list
/employees/create/
/employees/carga/                            → workload view
/employees/<id>/
/employees/<id>/view/
/employees/<id>/deactivate/

/clientes/, /clientes/nuevo/, /clientes/<id>/, /clientes/<id>/ver/, /clientes/<id>/deactivate/

# Notificaciones
/notificaciones/
/notificaciones/<id>/leer/
/notificaciones/leer-todas/

# Inventario (inventario/urls.py)
/proveedores/, /proveedores/nuevo/, /proveedores/<id>/, /proveedores/<id>/deactivate/
/insumos/, /insumos/nuevo/, /insumos/<id>/, /insumos/<id>/ver/, /insumos/<id>/deactivate/
/projects/<id>/insumos/nuevo/
/insumos-proyecto/<id>/
/insumos-proyecto/<id>/eliminar/
/insumos-proyecto/<id>/qr/
/compras/, /compras/nueva/, /compras/<id>/, /compras/<id>/deactivate/
/inventario/reporte/

# Pagos (pagos/urls.py)
/payments/, /payments/create/, /payments/<id>/, /payments/<id>/view/, /payments/<id>/deactivate/
/payments/filter/                            → AJAX filter by project name
/pagos-empleados/                            → list pagos a empleados
/contratos/empleado/<id>/pagos/nuevo/
/pagos-empleado/<id>/
/pagos-empleado/<id>/deactivate/
/payment-analysis/

# Reportes
/reporte-analisis/
/project_report/
```

## Settings Notes
- `AUTH_USER_MODEL = 'projects.Empleado'`
- `LOGIN_URL = '/signin'`, `LOGIN_REDIRECT_URL = '/dashboard/'`
- Session timeout: 1800s, `SESSION_SAVE_EVERY_REQUEST = True`
- `MEDIA_URL/MEDIA_ROOT` configured for contract documents and sede photos
- Templates: `BASE_DIR / 'projects' / 'templates'` and `BASE_DIR / 'templates'` (for base.html)
