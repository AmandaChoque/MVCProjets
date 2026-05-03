# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tesis

**Título**: *"Sistema web para la gestión de proyectos para una empresa que realiza instalaciones de sistemas de seguridad"*

**Caso de estudio**: SOBOTEC S.R.L.

El sistema cubre el ciclo completo de gestión: desde la captación del cliente y la planificación del proyecto, hasta el seguimiento de avance en campo (sedes, checklists, fotos), el control de costos (mano de obra por jornada + insumos FIFO), los pagos al cliente y a empleados, y la gestión de garantías post-entrega. Incluye reportes en PDF y Excel para respaldo documental.

## Empresa y Propósito del Sistema

**SOBOTEC S.R.L.** es una empresa boliviana dedicada a la **instalación, ampliación y mantenimiento de sistemas de seguridad** (cámaras IP/analógicas, DVR/NVR, alarmas y sensores).

### Tipos de proyecto y sus reglas de negocio

| Tipo | Descripción | Regla clave |
|---|---|---|
| `instalacion_nueva` | Instalación completa desde cero para un cliente | Incluye **1 año de garantía** a cargo de SOBOTEC: si algo falla en ese período, SOBOTEC cubre los costos sin cobrar al cliente |
| `ampliacion` | Ampliación de un sistema ya existente del cliente | Similar a instalación nueva pero sobre infraestructura preexistente |
| `mantenimiento_externo` | El cliente contrata a SOBOTEC para mantenimiento periódico de su sistema | Servicio recurrente; no implica instalación nueva |
| `emergencia` | Intervención urgente fuera de los contratos habituales | Naturaleza aún por definir; se modela igual que los demás tipos |

**Contrato de proyecto** (`ContratoProyecto`): fija fecha de entrega, monto acordado y penalidades por incumplimiento. Si SOBOTEC entrega después de `fecha_fin`, se acumula una multa diaria (% del monto) con un tope máximo configurado en el contrato.

### Equipo de trabajo y salarios

SOBOTEC asigna a cada proyecto un equipo formado típicamente por:
- **Instalador**: técnico líder, el más calificado. Dirige la instalación.
- **Técnico de soporte**: ayudante, conoce los fundamentos. Asiste al instalador.

Referencia de productividad: **4 cámaras en ~6 días** con 1 instalador + 1 técnico.

Los empleados no tienen sueldo fijo mensual; **se les paga por jornada trabajada**. El contrato interno (`ContratoEmpleado`) establece el monto total acordado y los días laborales (típico: 28 días). El `monto_diario` se calcula como `monto_acordado / dias_laborales`. Cada día trabajado queda registrado como una `JornadaEmpleado` (puede ser 0.5 o 1.0 días), que debe ser aprobada antes de generar el pago.

### Costos de un proyecto

El sistema rastrea dos componentes de costo por proyecto:
1. **Mano de obra**: suma de `JornadaEmpleado` aprobadas del equipo asignado al proyecto.
2. **Insumos**: materiales consumidos (cámaras, cables, DVR, sensores…) gestionados con stock FIFO a través del modelo `Requiere` + `RequiereLote`.

### Flujo completo

1. **Cliente** → **Proyecto** (con equipo de empleados asignado)
2. **Sedes**: puntos de instalación con checklist de tareas, fotos y geolocalización
3. **Contratos**: `ContratoEmpleado` (en `empleados/`) y `ContratoProyecto` (en `projects/`)
4. **Jornadas**: registro diario de trabajo del empleado por proyecto, con aprobación/rechazo
5. **Inventario**: insumos con stock FIFO automático. `Requiere` vincula insumos a proyectos
6. **Pagos**: `PagoProyecto` (cliente → proyecto) y `PagoEmpleado` (empresa → empleado)
7. **Garantía**: al completar un proyecto, se crea `Garantia` automáticamente si el contrato tiene `garantia_meses > 0`. Las incidencias post-entrega se registran como `IncidenciaGarantia` (costo absorbido por SOBOTEC)
8. **Reportes**: PDF y Excel para proyectos, empleados, inventario y pagos

El sistema es de uso interno con sesión de 30 minutos de timeout.

## Stack
- **Backend**: Django 5.1.2, SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Bootstrap 5.3 + Bootstrap Icons, HTML templates
- **PDF**: xhtml2pdf (pisa) — `?pdf` inline, `?pdf&download` fuerza descarga
- **Charts**: matplotlib (PNG base64 en HTML/PDF)
- **Excel**: openpyxl
- **QR codes**: qrcode (para insumos instalados en proyecto)
- **Server**: Gunicorn + WhiteNoise
- **Dates**: python-dateutil (`relativedelta` usado en cálculo de garantías)
- **Venv**: `venv/` (Windows)

## Development Commands
```bash
# Activar venv (Windows)
venv\Scripts\activate

# Servidor de desarrollo
python manage.py runserver

# Tras cambios en modelos
python manage.py makemigrations --name="descripcion_del_cambio"
python manage.py migrate

# Verificar errores de configuración
python manage.py check

# Tests (solo app projects tiene tests)
python manage.py test projects
python manage.py test projects.tests.PaymentFormCleanMontoTest
python manage.py test projects.tests.UpdatePaymentStatusTest
python manage.py test projects.tests.ContratoProyectoMultaTest
python manage.py test projects.tests.HistorialEstadoProyectoTest
python manage.py test projects.tests.HistorialPresupuestoTest
python manage.py test projects.tests.ContratoEmpleadoMontoDiarioTest
python manage.py test projects.tests.InsumoFormTest
python manage.py test projects.tests.CompraFormCleanCostoTest
```

## Architecture — Four Django Apps

`project_management/urls.py` es el root; hace `include()` de `empleados.urls` e `inventario.urls`. Las URLs de proyectos, clientes, sedes, pagos, plantillas y notificaciones se definen directamente en el root.

### `projects/` — App principal
- `models.py` — AuditModel (base abstracta), Cliente, Proyecto, AsignacionProyecto, ContratoProyecto, HistorialPresupuesto, HistorialEstadoProyecto, PlantillaTarea, ItemPlantilla, SubItemPlantilla, Sede, FotoSede, TareaChecklist, SubtareaChecklist, Notificacion, PagoProyecto, Garantia, IncidenciaGarantia. **Las señales están en este mismo archivo**: pre_save Proyecto (crea HistorialEstadoProyecto cuando cambia `estado_proyecto`, y HistorialPresupuesto cuando cambia `monto_total`); post_save Proyecto (recalcula `estado_pago` si cambió `monto_total`; crea `Garantia` via `crear_garantia_al_completar` cuando pasa a `completado` y el contrato tiene `garantia_meses > 0`); post_save TareaChecklist (sincroniza estado Sede/Proyecto y notifica); post_save/delete PagoProyecto (recalcula `estado_pago`).
- `signals.py` — solo una señal: post_save Sede copia items de PlantillaTarea a TareaChecklist al crear la sede
- `views.py` — todas las vistas de proyectos, clientes, sedes, tareas, fotos, plantillas, pagos y notificaciones (function-based)
- `form.py` — formularios (nombre del archivo es `form.py`, NO `forms.py`)
- `decorators.py` — `@cargo_required(*cargos)` para control de acceso por rol
- `context_processors.py` — inyecta en todos los templates: `user_cargo`, `es_admin`, `es_admin_o_gerente`, `es_admin_sec`, `es_campo`, `es_instalador_tecnico`, `notif_no_leidas`
- `validators.py` — validadores de contraseña (Uppercase, Lowercase, Number)

### `empleados/` — App de empleados
- `models.py` — Empleado (AbstractUser), ContratoEmpleado, PagoEmpleado, JornadaEmpleado
- `signals.py` — post_save JornadaEmpleado: fija `fecha_inicio` del proyecto en la primera jornada
- `views.py`, `urls.py`, `forms.py`

### `inventario/` — App de inventario
- `models.py` — Proveedor, Insumo, Requiere, Compra, RequiereLote, `calcular_costo_fifo()`. **Las señales de stock (Compra y Requiere post_save/delete) están al final de este archivo**
- `signals.py` — vacío (los handlers están en `models.py`)
- `views.py`, `urls.py`, `forms.py`

## Models Summary

### `projects/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `AuditModel` | created, updated_at, deleted_at, deleted_by, activo | Abstract base importado por todas las apps |
| `Cliente` | nit_ci, nombre, apellido_paterno, apellido_materno, rol_contacto, tipo_contratante, telefono, correo, direccion, nombre_entidad | Soft-delete via `delete()`. Managers: `objects` (activo=True), `all_objects`. `nombre_entidad` solo para `tipo_contratante='entidad_publica'` |
| `Proyecto` | codigo, nombre, descripcion, estado_proyecto, tipo_proyecto, fecha_inicio, fecha_fin, observacion, estado_pago, monto_total, FK→Cliente, FK→creado_por, M2M→Empleado(equipo) | `tipo_proyecto`: instalacion_nueva/ampliacion/mantenimiento_externo/emergencia. `_sync_estado_pago()` llamado por señal en PagoProyecto |
| `ContratoProyecto` | FK→Proyecto, fecha_firma, fecha_inicio, fecha_fin, monto_acordado, porcentaje_multa_diaria, porcentaje_multa_maxima, garantia_meses, observaciones, documento | Props: `dias_retraso`, `multa_acumulada`, `multa_tope_alcanzado`, `estado_multa` (normal/en_multa/critico). UniqueConstraint: un contrato activo por proyecto |
| `HistorialPresupuesto` | monto_anterior, monto_actual, motivo_cambio, FK→modificado_por, FK→Proyecto | Auto-creado por señal pre_save cuando cambia `monto_total` |
| `HistorialEstadoProyecto` | FK→Proyecto, estado_anterior, estado_nuevo, FK→cambiado_por, fecha, motivo | Auto-creado por señal pre_save cuando cambia `estado_proyecto`. Las vistas deben asignar `instance._current_user = request.user` antes de `save()` para registrar al responsable |
| `PlantillaTarea` | nombre, tipo (camara_ip/camara_analogica/dvr_nvr/alarma/sensor/otro), descripcion | Al crear Sede con plantilla, señal copia items como TareaChecklist |
| `ItemPlantilla` | FK→PlantillaTarea, descripcion, orden | |
| `SubItemPlantilla` | FK→ItemPlantilla, descripcion, orden | Sub-ítems opcionales de una tarea de plantilla |
| `Sede` | FK→Proyecto, FK→PlantillaTarea(nullable), nombre, direccion, descripcion, latitud, longitud, estado | `porcentaje_checklist` property. `_sync_estado()` actualiza estado según % de tareas completadas |
| `FotoSede` | FK→Sede, foto (ImageField `sedes/fotos/`), descripcion, FK→subida_por | |
| `TareaChecklist` | FK→Sede, descripcion, orden, completado, fecha_completado, FK→completado_por, M2M→participantes | Señal post_save sincroniza estado de Sede y Proyecto, y notifica admins/gerentes al 100% |
| `SubtareaChecklist` | FK→TareaChecklist, descripcion, orden, completado, fecha_completado, FK→completado_por | Sub-tareas opcionales de una tarea del checklist |
| `Notificacion` | FK→destinatario, tipo (sede_completada/tarea_completada/general), mensaje, leida, FK→Proyecto, FK→Sede, fecha | Solo admins/gerentes reciben notificaciones del sistema |
| `PagoProyecto` | FK→Proyecto(PROTECT), monto, descuento, motivo_descuento, fecha, tipo_pago, numero_referencia, estado | `estado`: pendiente/pagado (default `pagado`). `monto_neto` property = monto + descuento. `_sync_estado_pago()` solo cuenta pagos con `estado='pagado'`. Señal post_save/delete dispara `_sync_estado_pago()`, que usa `.update()` para no re-disparar señales del Proyecto. |
| `AsignacionProyecto` | FK→Proyecto, FK→Empleado, fecha_inicio_plan, fecha_fin_plan, dias_planificados | Planificación individual por empleado dentro de un proyecto. UniqueConstraint: (proyecto, empleado) activo. Props: `dias_reales` (jornadas aprobadas), `eficiencia_pct`, `dias_retraso`. Editable en `/proyectos/<id>/equipo/<id>/cronograma/` |
| `Garantia` | OneToOne→ContratoProyecto, fecha_inicio, fecha_vencimiento | Se crea automáticamente por señal `crear_garantia_al_completar` (post_save Proyecto) cuando pasa a `completado` y el contrato tiene `garantia_meses > 0`. fecha_vencimiento = fecha_inicio + relativedelta(months=garantia_meses). Props: `estado` (vigente/por_vencer/vencida), `dias_restantes`, `costo_total_incidencias` |
| `IncidenciaGarantia` | FK→Garantia, descripcion, fecha_reporte, fecha_reparacion, costo_reparacion, FK→reparado_por, estado, evidencia (FileField `garantias/evidencias/`) | estado: pendiente/en_reparacion/resuelto. `costo_reparacion` es absorbido por SOBOTEC (no se cobra al cliente). Requiere `fecha_reparacion` cuando estado=resuelto |

### `empleados/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `Empleado` | nombre, apellido_paterno, apellido_materno, cargo, carnet_identidad (unique), numero_celular | Extiende `AbstractUser`. cargo: administrador/gerente/instalador/tecnico_soporte/secretaria |
| `ContratoEmpleado` | FK→Empleado, tipo_contrato, dias_laborales (default=28), fecha_firma, fecha_inicio, fecha_fin, monto_acordado, observaciones, documento | `tipo_contrato`: diario (pago por jornada) o mensual (salario fijo). `monto_diario` property = monto_acordado / dias_laborales si diario; = monto_acordado si mensual. UniqueConstraint: un contrato activo por empleado |
| `PagoEmpleado` | FK→ContratoEmpleado(PROTECT), monto, fecha, tipo_pago, concepto | concepto: pago_jornada/adelanto/liquidacion/dia_extra/otro. UniqueConstraint: una liquidacion activa por contrato |
| `JornadaEmpleado` | FK→ContratoEmpleado, FK→Proyecto, FK→PagoEmpleado(nullable), FK→registrado_por, fecha, dias (0.5/1.0), observacion, estado, motivo_rechazo | estado: pendiente/aprobada/rechazada. `monto` property = dias × contrato.monto_diario. `clean()` valida que el empleado esté en el equipo del proyecto |

### `inventario/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `Proveedor` | nombre, rubro, nit, telefono, correo, direccion, encargado_nombre/cargo/celular | rubro: camaras_seguridad/cables_conectores/equipos_red/alarmas_perifoneo/sensores/computo/distribuidor/otro |
| `Insumo` | nombre, marca, modelo, categoria, unidad_medida, ultimo_precio_compra, stock, stock_minimo | `stock` y `ultimo_precio_compra` mantenidos exclusivamente por señales — **nunca modificar directamente**. `stock_status` property → agotado/bajo/ok. categoria incluye: camara_ip/camara_analogica/nvr_dvr/alarma_sonora/alarma_gsm/perifoneo/sensor/cable/fuente/bateria/pantalla/red/instalacion |
| `Requiere` | FK→Proyecto, FK→Insumo, cantidad, durante_garantia | `costo_total` property calculado desde lotes FIFO. `durante_garantia` se setea automáticamente en la vista según si el proyecto tiene garantía activa al momento de agregar el insumo. UniqueConstraint: único activo por (proyecto, insumo) |
| `Compra` | FK→Proveedor, FK→Insumo, cantidad, costo_unitario, fecha, numero_factura | `costo_total` property = cantidad × costo_unitario (no almacenado en BD) |
| `RequiereLote` | FK→Requiere, FK→Compra, cantidad | Trazabilidad FIFO. Managers: `objects` (activos), `all_objects` |

`calcular_costo_fifo(insumo, cantidad, excluir_requiere_pk=None)` — función en `inventario/models.py` que consume compras por fecha FIFO y retorna lista de lotes a consumir. Lanza `ValueError` si stock insuficiente.

## Key Patterns

**Soft-delete**: `activo=False`. Solo `Cliente` overridea `delete()`. Resto: vistas `deactivate_*` setean `activo=False` directamente. Hard delete (`project_delete`) es la excepción, solo para proyectos.

**Forms**: Campos monetarios usan `CharField` + `clean_*` con regex `r'\d+(\.\d{1,2})?'` (sin comas, punto decimal). Widgets Bootstrap `form-control`/`form-select`. Forms en `form.py` (projects) o `forms.py` (empleados, inventario).

**Views**: Todas usan `@login_required`. Patrón: GET retorna form, POST valida y redirige. `messages.success()` en create/update. `get_object_or_404()` para lookups.

**Role-based access**: `@cargo_required(*cargos)` de `projects/decorators.py` después de `@login_required`. Grupos predefinidos en decorators: `ROLES_ADMIN = ('administrador', 'gerente')`, `ROLES_ADMIN_SEC` (+ secretaria), `ROLES_CAMPO` (+ instalador, tecnico_soporte), `ROLES_INSTALADOR` (+ instalador, sin tecnico_soporte). Superusers bypasean todo. Templates usan `{% if es_admin %}`, `{% if es_campo %}`, `{% if es_instalador_tecnico %}`.

**Empleado es el User model**: `AUTH_USER_MODEL = 'empleados.Empleado'`. Cargo del usuario: `request.user.cargo`.

**Paginación**: `Paginator` con `per_page` configurable (10/20/50/100) via GET param.

**Stock management**: `Insumo.stock` es desnormalizado, mantenido exclusivamente por señales en `inventario/models.py`. Lo mismo para `ultimo_precio_compra`.

**METODOS_PAGO**: `[('efectivo', ...), ('transferencia', ...)]` está definida por duplicado: una vez en `empleados/models.py` (usada por `PagoEmpleado`) y otra vez en `projects/models.py` (usada por `PagoProyecto`). No hay una constante compartida; son copias independientes.

## URL Structure

Las URLs están en español. Las URLs de proyectos, clientes, sedes, pagos, plantillas y notificaciones van en el root `urls.py`; empleados e inventario tienen sus propios `urls.py`.

```
/                                                → landing
/dashboard/                                      → home
/signin/, /signup/, /signout/
/extend-session/                                 → AJAX session extension (POST)
/cambiar-contrasena/

# Proyectos
/proyectos/
/proyectos/nuevo/
/proyectos/analisis/
/proyectos/seguimiento/                          → seguimiento_avance
/proyectos/financiero/                           → analisis_financiero
/proyectos/planificacion/                        → planificacion_gantt (Gantt chart de AsignacionProyecto)
/proyectos/calendario/                           → calendario_equipo (calendario de jornadas del equipo)
/proyectos/reporte/
/proyectos/<id>/
/proyectos/<id>/ver/
/proyectos/<id>/completar/
/proyectos/<id>/eliminar/                        → hard delete
/proyectos/<id>/desactivar/

# Sedes de instalación
/proyectos/<id>/sedes/nueva/
/sedes/<id>/
/sedes/<id>/ver/
/sedes/<id>/desactivar/
/sedes/<id>/tareas/nueva/
/sedes/<id>/tareas/reordenar/
/sedes/<id>/aplicar-plantilla/
/sedes/<id>/fotos/subir/
/tareas/<id>/alternar/
/tareas/<id>/participantes/
/tareas/<id>/editar/
/tareas/<id>/eliminar/
/tareas/<id>/subtareas/nueva/
/subtareas/<id>/alternar/
/subtareas/<id>/eliminar/
/fotos/<id>/eliminar/

# Equipo del proyecto
/proyectos/<id>/equipo/agregar/
/proyectos/<id>/equipo/<id_employee>/remover/
/proyectos/<id>/equipo/<id_employee>/cronograma/          → editar AsignacionProyecto (fechas y días planificados)

# Contratos de proyecto
/proyectos/<id>/contrato-proyecto/nuevo/
/contratos/proyecto/<id>/
/contratos/proyecto/<id>/desactivar/

# Clientes
/clientes/, /clientes/nuevo/, /clientes/<id>/, /clientes/<id>/ver/, /clientes/<id>/desactivar/

# Plantillas de tareas
/plantillas/, /plantillas/nueva/, /plantillas/<id>/, /plantillas/<id>/desactivar/
/plantillas/<id>/items/nuevo/
/plantillas/<id>/items/reordenar/
/plantillas/items/<id>/editar/
/plantillas/items/<id>/eliminar/
/plantillas/items/<id>/subitems/nuevo/
/plantillas/subitems/<id>/eliminar/

# Notificaciones
/notificaciones/
/notificaciones/<id>/leer/
/notificaciones/leer-todas/

# Pagos del cliente al proyecto
/pagos/, /pagos/nuevo/, /pagos/<id>/, /pagos/<id>/ver/, /pagos/<id>/desactivar/
/pagos/<id>/confirmar/                           → confirmar_pago_proyecto (confirmación GET/POST antes de desactivar)
/pagos/filtrar/                                  → AJAX filter por nombre de proyecto
/pagos/analisis/

# Empleados (empleados/urls.py)
/empleados/, /empleados/nuevo/, /empleados/carga/, /empleados/reporte/
/empleados/<id>/, /empleados/<id>/ver/, /empleados/<id>/desactivar/
/mi-trabajo/                                     → dashboard instalador

# Contratos de empleado
/empleados/<id>/contratos/nuevo/
/contratos/empleado/<id>/
/contratos/empleado/<id>/desactivar/
/contratos/empleado/<id>/pdf/

# Jornadas
/contratos/empleado/<id>/jornadas/nueva/
/jornadas/<id>/
/jornadas/<id>/eliminar/
/jornadas/<id>/aprobar/
/jornadas/<id>/rechazar/
/proyectos/<id>/jornadas/revision/

# Pagos a empleados
/pagos-empleados/
/contratos/empleado/<id>/pagos/nuevo/
/pagos-empleado/<id>/
/pagos-empleado/<id>/confirmar/                  → confirmar_pago_empleado
/pagos-empleado/<id>/desactivar/

# Inventario (inventario/urls.py)
/proveedores/, /proveedores/nuevo/, /proveedores/<id>/, /proveedores/<id>/desactivar/
/insumos/, /insumos/nuevo/, /insumos/<id>/, /insumos/<id>/ver/, /insumos/<id>/desactivar/
/proyectos/<id>/insumos/nuevo/
/insumos-proyecto/<id>/
/insumos-proyecto/<id>/eliminar/
/compras/, /compras/nueva/, /compras/<id>/, /compras/<id>/desactivar/
/inventario/reporte/
```

> Nota: `/insumos-proyecto/<id>/qr/` está definida en `project_management/urls.py` (root), no en `inventario/urls.py`.

```
# Garantías post-instalación
/garantias/
/garantias/<id>/
/garantias/<id>/incidencias/nueva/
/garantias/incidencias/<id>/
/garantias/incidencias/<id>/desactivar/
```

## Settings Notes
- `AUTH_USER_MODEL = 'empleados.Empleado'`
- `LOGIN_URL = '/signin'`, `LOGIN_REDIRECT_URL = '/dashboard/'`
- Session timeout: 1800s, `SESSION_SAVE_EVERY_REQUEST = True`, `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`
- `MEDIA_URL/MEDIA_ROOT` para documentos de contratos y fotos de sedes
- Templates dirs: `BASE_DIR / 'templates'` (base.html), `BASE_DIR / 'projects' / 'templates'`, `BASE_DIR / 'empleados' / 'templates'`; además `APP_DIRS = True` para el resto
