# MVCProjets - Django Project Management App

## Project Overview
Django MVC web application for managing projects, clients, employees, payments, proposals, and public entities. Used for internal business workflows.

## Stack
- **Backend**: Django 5.1.2 (Python), SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Bootstrap + HTML templates (xhtml2pdf, reportlab for PDF, matplotlib for charts)
- **Server**: Gunicorn + WhiteNoise (static files)
- **Venv**: `venv/` (Windows)

## Development Setup
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Run development server
python manage.py runserver

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## Project Structure
```
MVCProjets/
├── project_management/    # Django project config
│   ├── settings.py
│   └── urls.py            # All URL routing
├── projects/              # Main app
│   ├── models.py          # All models
│   ├── views.py           # All views (function-based)
│   ├── form.py            # All forms
│   ├── admin.py
│   ├── migrations/        # Single migration: 0001_initial.py
│   └── templates/         # HTML templates
├── static/                # Static assets
└── manage.py
```

## Key Models (projects/models.py)
- **Cliente**: cargo, nit_ci, nombre, apellido_paterno, apellido_materno, telefono, direccion, tipo_contratante (empresa/personal/entidad_publica), activo. Has `ActiveClienteManager` (default) and `all_objects`. Soft-delete via `delete()`.
- **Empleado**: linked to User (OneToOne), nombre, apellidos, cargo (gerente_general/tecnico/analista/desarrollador), carnet_identidad, activo
- **Proyecto**: codigo, nombre, estado_proyecto (pendiente/en_progreso/completado), tipo_proyecto (licitacion/contratacion_directa), estado_pago, monto_total, FK→User/Empleado/Cliente/Propuesta
- **Pago**: monto, fecha, estado (pagado/pendiente), tipo_pago (parcial/completo), FK→Proyecto. Signal updates project payment status on post_save.
- **EntidadPublica**: representante_legal, contacto, direccion, nombre_entidad
- **Propuesta**: fecha_presentacion, monto_presupuesto, requisitos, FK→EntidadPublica

## Key Patterns
- All views use `@login_required`
- Soft-delete: `activo=False` instead of real DB delete (Cliente, Empleado, etc.)
- Function-based views only (no CBVs)
- Forms in `projects/form.py` (not `forms.py`)
- Pagination in `clientes` view: configurable per_page (10/20/50/100)
- Search/filter in `clientes` view: Q objects on nombre, nit_ci (icontains), tipo_contratante

## URL Patterns (project_management/urls.py)
- `/` → landing, `/dashboard/` → home
- `/projects/`, `/employees/`, `/payments/`, `/public_entities/`, `/proposals/`, `/clientes/`
- Reports: `/reporte-analisis/`, `/project_report/`, `/payment-analysis/`
- Auth: `/signup/`, `/signin/`, `/signout/`, `/extend-session/`

## Settings Notes
- `LOGIN_URL = '/signin'`, `LOGIN_REDIRECT_URL = '/dashboard/'`
- Session timeout: 1800s (30 min), `SESSION_SAVE_EVERY_REQUEST = True`
- Static files: `STATICFILES_DIRS = [BASE_DIR / "static"]`, `STATIC_ROOT = staticfiles/`
- Templates dir: `BASE_DIR / 'projects' / 'templates'`
