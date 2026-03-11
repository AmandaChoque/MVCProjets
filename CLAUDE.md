# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Empresa y Propósito del Sistema

**SOBOTEC S.R.L.** es una empresa boliviana dedicada a la **instalación, ampliación y mantenimiento de sistemas de seguridad** (cámaras IP/analógicas, DVR/NVR, alarmas y sensores).

Este sistema web gestiona el ciclo completo de un proyecto de seguridad:
1. **Captación**: Se registra un cliente (empresa, persona o entidad pública) y se vincula a una propuesta/licitación.
2. **Proyecto**: Se crea el proyecto (tipo: instalación nueva, ampliación, mantenimiento o emergencia), se asigna un empleado responsable y se controla su estado (pendiente → en progreso → completado).
3. **Contratos**: Se generan contratos con el cliente (ContratoProyecto) y con los empleados asignados (ContratoEmpleado), con documentos adjuntos.
4. **Insumos y compras**: Se catalogan los insumos/equipos (cámaras, cables, fuentes, etc.) por categoría. Se registra qué insumos requiere cada proyecto (Requiere) y qué compras se realizan a proveedores (Realizar).
5. **Progreso**: Se registra el avance porcentual del proyecto con observaciones.
6. **Pagos**: Se registran los pagos del cliente al proyecto (parciales o completos). Una señal Django actualiza automáticamente el `estado_pago` del proyecto.
7. **Reportes**: Se generan reportes PDF y gráficos de análisis para proyectos y pagos.

El sistema es de uso interno, con autenticación de usuarios y sesión con timeout de 30 minutos.

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
```

## Architecture

All code lives in a single Django app `projects/`:
- `models.py` — all models
- `views.py` — all views (function-based, ~1000 lines)
- `form.py` — all forms (NOT `forms.py`)
- `admin.py` — admin registrations
- `migrations/` — 14 migrations (0001–0014)
- `templates/` — all HTML templates (~50 files), extend `base.html`

URL routing is entirely in `project_management/urls.py` (single file, ~120 lines).

## Models Summary

| Model | Key fields | Notes |
|---|---|---|
| `AuditModel` | created, updated_at, deleted_at, activo | Abstract base |
| `Cliente` | nit_ci, nombre, apellidos, cargo, tipo_contratante, activo | Soft-delete via `delete()`. `ActiveClienteManager` (default, activo=True), `all_objects` |
| `Empleado` | user (OneToOne→User), nombre, apellidos, cargo, carnet_identidad, activo | cargo choices: administrador/gerente/instalador/tecnico_soporte/secretaria |
| `EntidadPublica` | nombre_entidad, representante_legal, contacto, direccion | |
| `Propuesta` | fecha_presentacion, monto_presupuesto, requisitos, FK→EntidadPublica | |
| `Proyecto` | codigo, nombre, estado_proyecto, tipo_proyecto, estado_pago, monto_total, FK→User/Cliente/Propuesta | Extends AuditModel. tipo_proyecto: instalacion_nueva/ampliacion/mantenimiento/emergencia |
| `Pago` | monto, fecha, estado, tipo_pago, FK→Proyecto | post_save signal → `update_project_payment_status()` |
| `HistorialPago` | monto_anterior, monto_actual, motivo_cambio, FK→Proyecto | |
| `Progreso` | proyecto, fecha, porcentaje (0-100), descripcion, observacion | Cannot decrease porcentaje (enforced in ProgresoForm) |
| `ContratoEmpleado` | empleado, proyecto, fechas, monto_acordado, documento | FileField: PDF/JPG/PNG/GIF/WEBP |
| `ContratoProyecto` | proyecto (OneToOne), fechas, monto_acordado, documento | One per project |
| `Proveedor` | nombre, rubro, celular, correo, direccion, nit, activo | |
| `Insumo` | nombre, marca, categoria, costo_unitario, activo | categoria choices: camara_ip/camara_analogica/nvr_dvr/alarma/sensor/cable/fuente/accesorio |
| `Requiere` | proyecto, insumo, cantidad, costo_unitario | `@property subtotal = cantidad × costo_unitario`. Price copied at assignment time |
| `Realizar` | proveedor, insumo, cantidad, costo_unitario, costo_total, fecha | costo_total calculated in view before save |

## Key Patterns

**Soft-delete**: Set `activo=False` instead of deleting. `Cliente` overrides `delete()`. Other models set `activo=False` in views directly.

**Forms**: All forms use Bootstrap `form-control`/`form-select` widgets. Decimal fields (monto, costo_unitario, salario) use `CharField` + `clean_*` with regex `r'\d+(\.\d{1,2})?'` — no commas, dot as decimal separator.

**Views**: All use `@login_required`. Pattern: GET returns form, POST validates and redirects. Use `messages.success()` on create/update. Use `get_object_or_404()`.

**Pagination**: `Paginator` with configurable `per_page` (10/20/50/100) via GET param. Applied to projects, employees, payments, clients, proveedores, insumos, compras.

**PDF export**: `?pdf` renders inline, `?pdf&download` forces download. Uses `xhtml2pdf.pisa.CreatePDF`.

**project_view**: Aggregates progresos, contratos_empleados, contrato_proyecto, insumos_proyecto, total_insumos in a single view.

## URL Structure

```
/                          → landing
/dashboard/                → home (login required)
/projects/<id>/view/       → full project detail with all related data
/projects/<id>/insumos/nuevo/  → add insumo to project (Requiere)
/insumos-proyecto/<id>/    → edit Requiere
/proveedores/              → supplier CRUD
/insumos/                  → equipment catalog CRUD
/compras/                  → purchases (Realizar) CRUD
```

## Settings Notes
- `LOGIN_URL = '/signin'`, `LOGIN_REDIRECT_URL = '/dashboard/'`
- Session timeout: 1800s, `SESSION_SAVE_EVERY_REQUEST = True`
- `MEDIA_URL/MEDIA_ROOT` configured for contract document uploads
- Templates: `BASE_DIR / 'projects' / 'templates'`
