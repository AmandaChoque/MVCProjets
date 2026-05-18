# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tesis

**Título**: *"Sistema web para la gestión de proyectos para una empresa que realiza instalaciones de sistemas de seguridad"*

**Caso de estudio**: SOBOTEC S.R.L.

El sistema cubre el ciclo completo: captación del cliente → planificación del proyecto → seguimiento en campo (sedes, checklists, fotos) → control de costos (jornadas + insumos FIFO) → pagos al cliente y empleados → garantías post-entrega. Incluye reportes PDF y Excel.

## Empresa

**SOBOTEC S.R.L.** instala, amplía y mantiene sistemas de seguridad (cámaras IP/analógicas, DVR/NVR, alarmas, sensores) en Bolivia.

### Tipos de proyecto y reglas de negocio

| Tipo | Descripción | Regla clave |
|---|---|---|
| `instalacion_nueva` | Instalación completa desde cero | Incluye garantía a cargo de SOBOTEC (`ContratoProyecto.garantia_meses`): si algo falla en ese período, SOBOTEC cubre los costos sin cobrar al cliente |
| `mantenimiento_externo` | Mantenimiento periódico del sistema del cliente | Servicio recurrente; no implica instalación nueva |

**Equipo**: instalador (técnico líder) + técnico de soporte. Referencia: ~4 cámaras en 6 días.

**Jornadas**: no hay sueldo fijo. El `ContratoEmpleado` establece `monto_acordado` y `dias_laborales` (típico: 28). El `monto_diario = monto_acordado / dias_laborales`. Cada día trabajado es una `JornadaEmpleado` (0.5 o 1.0 días), que debe aprobarse antes de generar pago.

**Multas**: `ContratoProyecto` tiene `porcentaje_multa_diaria` y tope `porcentaje_multa_maxima`. Si el proyecto entrega después de `fecha_fin`, se acumula multa diaria hasta el tope. `estado_multa`: normal / en_multa / critico.

## Stack

- **Backend**: Django 6.0.1, SQLite (dev) / PostgreSQL (prod con `dj_database_url`)
- **Frontend**: Bootstrap 5.3 + Bootstrap Icons, templates HTML
- **PDF**: xhtml2pdf (pisa) — `?pdf` inline, `?pdf&download` descarga
- **Charts**: matplotlib (PNG base64 en HTML/PDF)
- **Excel**: openpyxl
- **QR**: qrcode
- **Server**: Gunicorn + WhiteNoise
- **Dates**: python-dateutil (`relativedelta` para garantías)
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

`project_management/urls.py` es el root; hace `include('empleados.urls')` e `include('inventario.urls')`. Todas las URLs de proyectos, clientes, sedes, pagos, plantillas, garantías y notificaciones van directamente en el root.

### `projects/` — App principal

- `models.py` — AuditModel (base abstracta), Cliente, Proyecto, AsignacionProyecto, ContratoProyecto, HistorialPresupuesto, HistorialEstadoProyecto, PlantillaTarea, ItemPlantilla, SubItemPlantilla, Sede, FotoSede, TareaChecklist, SubtareaChecklist, Notificacion, PagoProyecto, Garantia, IncidenciaGarantia. **Las señales de Proyecto, PagoProyecto y TareaChecklist están al final de este mismo archivo** (pre_save registra HistorialEstadoProyecto/HistorialPresupuesto; post_save crea Garantía al completar, desactiva contrato al cancelar; post_save/delete PagoProyecto recalcula `estado_pago`; post_save TareaChecklist sincroniza Sede/Proyecto y crea JornadaEmpleado automática).
- `signals.py` — solo una señal: post_save Sede copia items de PlantillaTarea a TareaChecklist/SubtareaChecklist al crear la sede.
- `views.py` — todas las vistas (function-based)
- `form.py` — formularios (nombre del archivo es `form.py`, NO `forms.py`)
- `decorators.py` — `@cargo_required(*cargos)` para control de acceso por rol
- `context_processors.py` — inyecta en todos los templates: `user_cargo`, `es_admin`, `es_admin_o_gerente`, `es_admin_sec`, `es_campo`, `es_instalador_tecnico`, `notif_no_leidas`
- `validators.py` — validadores de contraseña: `UppercaseValidator`, `LowercaseValidator`, `NumberValidator`

### `empleados/` — App de empleados

- `models.py` — Empleado (AbstractUser), ContratoEmpleado, PagoEmpleado, JornadaEmpleado
- `signals.py` — vacío de contenido relevante (la señal de jornada automática está en `projects/models.py`)
- `views.py`, `urls.py`, `forms.py`

### `inventario/` — App de inventario

- `models.py` — Proveedor, Insumo, Requiere, Compra, RequiereLote, `calcular_costo_fifo()`. **Las señales de stock (Compra y Requiere post_save/delete) están al final de este archivo**, NO en `signals.py`.
- `signals.py` — vacío
- `views.py`, `urls.py`, `forms.py`

## Models — Choices completos

### `projects/models.py`

**Cliente**
- `tipo_contratante`: `personal` / `entidad_publica`
- `rol_contacto`: `propietario` / `encargado` / `gerente` / `representante`

**Proyecto**
- `estado_proyecto`: `pendiente` / `en_progreso` / `completado` / `cancelado`
- `tipo_proyecto`: `instalacion_nueva` / `mantenimiento_externo`
- `estado_pago` (desnormalizado, solo señales): `no_pagado` / `parcial` / `pagado`

**PlantillaTarea**
- `tipo`: `camara_ip` / `camara_analogica` / `dvr_nvr` / `alarma` / `sensor` / `otro`

**Sede**
- `estado`: `pendiente` / `en_progreso` / `completado`

**Notificacion**
- `tipo`: `sede_completada` / `tarea_completada` / `general`

**PagoProyecto**
- `tipo_pago` (`METODOS_PAGO` definida en `projects/models.py`): `efectivo` / `transferencia`
- `estado`: `pendiente` / `pagado`

**IncidenciaGarantia**
- `estado`: `pendiente` / `en_reparacion` / `resuelto`

**HistorialEstadoProyecto**
- `estado_anterior` / `estado_nuevo`: `pendiente` / `en_progreso` / `completado` / `cancelado`

### `empleados/models.py`

**Empleado**
- `cargo`: `administrador` / `gerente` / `instalador` / `tecnico_soporte` / `secretaria`

**PagoEmpleado**
- `concepto`: `pago_jornada` / `adelanto` / `liquidacion`
- `estado`: `pendiente` / `pagado`

**JornadaEmpleado**
- `dias` (DecimalField): `0.5` (medio día) / `1.0` (día completo) — choices del modelo usan strings `'0.5'` / `'1.0'`
- `estado`: `pendiente` / `aprobada` / `rechazada`

### `inventario/models.py`

**Proveedor**
- `rubro`: `camaras_seguridad` / `cables_conectores` / `equipos_red` / `alarmas_perifoneo` / `sensores` / `computo` / `distribuidor` / `otro`

**Insumo**
- `categoria`: `camara_ip` / `camara_analogica` / `nvr_dvr` / `alarma_sonora` / `alarma_gsm` / `perifoneo` / `sensor` / `cable` / `fuente` / `bateria` / `pantalla` / `red` / `instalacion`
- `unidad_medida`: `unidad` / `metro` / `rollo` / `caja` / `par`

## Models Summary

### `projects/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `AuditModel` | created, updated_at, deleted_at, deleted_by, modificado_por, activo | Abstract base. `_modified_by` attr en save() setea `modificado_por` |
| `Cliente` | nit_ci, nombre, apellido_paterno, apellido_materno, rol_contacto, tipo_contratante, telefono, correo, direccion, nombre_entidad | Soft-delete via `delete()`. Managers: `objects` (activo=True), `all_objects`. `nombre_entidad` solo para `entidad_publica` |
| `Proyecto` | codigo (unique), nombre (unique), descripcion, estado_proyecto, tipo_proyecto, fecha_inicio, fecha_fin, observacion, estado_pago, monto_total, FK→Cliente(PROTECT), FK→creado_por, M2M→Empleado(equipo) | `_sync_estado_pago()` recalcula desde PagoProyecto con `.update()` para no re-disparar señales |
| `AsignacionProyecto` | FK→Proyecto, FK→Empleado, fecha_inicio_plan, fecha_fin_plan, dias_planificados | Cronograma planificado por empleado (no reemplaza M2M equipo). Props: `dias_reales` (jornadas aprobadas), `eficiencia_pct`, `dias_retraso`, `estado_asignacion` (pendiente/en_curso/por_vencer/vencida/completada/cancelado), `pct_avance`. UniqueConstraint: (proyecto, empleado) activo |
| `ContratoProyecto` | FK→Proyecto, fecha_firma, fecha_inicio, fecha_fin, monto_acordado, porcentaje_multa_diaria, porcentaje_multa_maxima, garantia_meses, observaciones, documento | Props: `dias_retraso`, `multa_acumulada`, `multa_tope_alcanzado`, `porcentaje_multa_sobre_contrato`, `estado_multa` (normal/en_multa/critico). UniqueConstraint: un contrato activo por proyecto |
| `HistorialPresupuesto` | FK→Proyecto, monto_anterior, monto_actual, motivo_cambio, FK→modificado_por | Auto-creado por señal pre_save cuando cambia `monto_total` |
| `HistorialEstadoProyecto` | FK→Proyecto, estado_anterior, estado_nuevo, FK→cambiado_por, fecha, motivo | Auto-creado por señal pre_save cuando cambia `estado_proyecto`. Vistas deben asignar `instance._current_user = request.user` antes de `save()` |
| `PlantillaTarea` | nombre, tipo, descripcion | Al crear Sede con plantilla, señal en `projects/signals.py` copia items como TareaChecklist |
| `ItemPlantilla` | FK→PlantillaTarea, descripcion, orden | |
| `SubItemPlantilla` | FK→ItemPlantilla, descripcion, orden | |
| `Sede` | FK→Proyecto, nombre, direccion, descripcion, latitud, longitud, estado, FK→PlantillaTarea(nullable) | `porcentaje_checklist` property. `_sync_estado()` actualiza estado según % completado |
| `FotoSede` | FK→Sede, foto (ImageField `sedes/fotos/`), descripcion, FK→subida_por | |
| `TareaChecklist` | FK→Sede, descripcion, orden, completado, fecha_completado, FK→completado_por, M2M→participantes | Señal post_save sincroniza estado Sede/Proyecto y notifica admins/gerentes al 100% vía `bulk_create` |
| `SubtareaChecklist` | FK→TareaChecklist, descripcion, orden, completado, fecha_completado, FK→completado_por | |
| `Notificacion` | FK→destinatario, tipo, mensaje, leida (db_index), FK→Proyecto, FK→Sede, fecha | Solo admins/gerentes reciben notificaciones del sistema |
| `PagoProyecto` | FK→Proyecto(PROTECT), monto, descuento, motivo_descuento, fecha (db_index), tipo_pago, numero_referencia, estado | `monto_neto` property = monto + descuento. Señal post_save/delete → `_sync_estado_pago()` |
| `Garantia` | OneToOne→ContratoProyecto, fecha_inicio, fecha_vencimiento | Auto-creada por señal cuando proyecto pasa a `completado` y contrato tiene `garantia_meses > 0`. Props: `estado` (vigente/por_vencer/vencida), `dias_restantes`, `costo_total_incidencias` |
| `IncidenciaGarantia` | FK→Garantia, descripcion, fecha_reporte, fecha_reparacion, costo_reparacion, FK→reparado_por, estado, evidencia (FileField `garantias/evidencias/`) | Costo absorbido por SOBOTEC. Requiere `fecha_reparacion` cuando estado=resuelto |

### `empleados/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `Empleado` | nombre, apellido_paterno, apellido_materno, cargo, carnet_identidad (unique), numero_celular | Extiende AbstractUser. `activo` property mapea a `is_active`. `get_full_name()` concatena nombre + apellidos |
| `ContratoEmpleado` | FK→Empleado, dias_laborales (default=28), fecha_firma, fecha_inicio, fecha_fin, monto_acordado, observaciones, documento | `monto_diario` = monto_acordado / dias_laborales. Props: `vigente`, `estado_contrato` (vigente/vencido/inhabilitado), `dias_hasta_vencimiento`. UniqueConstraint: un contrato activo por empleado |
| `PagoEmpleado` | FK→ContratoEmpleado(PROTECT), monto, fecha (db_index), concepto, estado | UniqueConstraint: solo una liquidacion activa por contrato |
| `JornadaEmpleado` | FK→ContratoEmpleado, FK→Proyecto, FK→PagoEmpleado(nullable), fecha, dias (0.5/1.0), observacion, estado, motivo_rechazo, FK→registrado_por | `clean()` valida: pago.contrato == jornada.contrato, empleado en equipo del proyecto, fecha en rango del contrato. Límite 0.5/1.0 días lo impone MaxValueValidator + CheckConstraint `jornada_dias_validos`. `monto` property = dias × contrato.monto_diario. UniqueConstraint: (contrato, proyecto, fecha) activo |

### `inventario/models.py`

| Model | Key fields | Notes |
|---|---|---|
| `Proveedor` | nombre, rubro, nit, telefono, correo, direccion, encargado_nombre/cargo/celular | UniqueConstraint NIT cuando no vacío. `db_table = 'inventario_proveedor'` |
| `Insumo` | nombre, marca, modelo, categoria, unidad_medida, ultimo_precio_compra, stock, stock_minimo | `stock` y `ultimo_precio_compra` mantenidos SOLO por señales. `stock_status` property → agotado/bajo/ok. `_recalculate_stock()` = compras − asignados. UniqueConstraint: (nombre, marca, modelo) activo |
| `Requiere` | FK→Proyecto, FK→Insumo(SET_NULL), cantidad, durante_garantia | `costo_total` property suma lotes FIFO. `durante_garantia` se setea en la vista. UniqueConstraint: (proyecto, insumo) activo |
| `Compra` | FK→Proveedor(SET_NULL), FK→Insumo(SET_NULL), cantidad, costo_unitario, fecha, numero_factura | `costo_total` property = cantidad × costo_unitario (no almacenado). SET_NULL preserva historial |
| `RequiereLote` | FK→Requiere, FK→Compra, cantidad | Trazabilidad FIFO. Managers: `objects` (activos), `all_objects`. `subtotal` property. UniqueConstraint: (requiere, compra) activo |

`calcular_costo_fifo(insumo, cantidad, excluir_requiere_pk=None)` — función en `inventario/models.py` que consume compras por fecha FIFO (luego por `created`). Lanza `ValueError` si stock insuficiente. Usa 2 queries en lugar de 1 por lote.

## Key Patterns

**Soft-delete**: `activo=False`. Solo `Cliente` overridea `delete()`. El resto usa vistas `deactivate_*` que setean `activo=False` directamente. Hard delete (`project_delete`) es excepción solo para proyectos.

**Forms**: Campos monetarios usan `CharField` + `clean_*` con `DECIMAL_REGEX = r'\d+(\.\d{1,2})?'` (sin comas, punto decimal). Todos los widgets usan Bootstrap `form-control`/`form-select`. Forms de projects están en `form.py` (NO `forms.py`); empleados e inventario usan `forms.py`.

**Views**: Todas usan `@login_required`. Patrón: GET retorna form, POST valida y redirige. `messages.success()` en create/update. `get_object_or_404()` para lookups.

**Role-based access**: `@cargo_required(*cargos)` de `projects/decorators.py` siempre después de `@login_required`. Grupos predefinidos:
- `ROLES_ADMIN = ('administrador', 'gerente')`
- `ROLES_ADMIN_SEC = ('administrador', 'gerente', 'secretaria')`
- `ROLES_CAMPO = ('administrador', 'gerente', 'instalador', 'tecnico_soporte')`
- `ROLES_INSTALADOR = ('administrador', 'gerente', 'instalador')`

Superusers bypasean todo. Templates usan `{% if es_admin %}`, `{% if es_campo %}`, `{% if es_instalador_tecnico %}`.

**Paginación**: `Paginator` con `per_page` configurable (10/20/50/100) via GET param.

**Stock management**: `Insumo.stock` e `Insumo.ultimo_precio_compra` son desnormalizados, mantenidos EXCLUSIVAMENTE por señales al final de `inventario/models.py`. Nunca modificar directamente.

**METODOS_PAGO**: `[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia')]` definida en `projects/models.py` (para `PagoProyecto`). Son copias independientes — no hay constante compartida.

**AJAX inline creation**: Endpoints `…/ajax/nuevo/` (clientes, proveedores, insumos) crean objetos desde modal retornando JSON `{id, nombre}`. Mismos decoradores que sus contrapartes normales.

**Historial de estado**: Vistas deben asignar `instance._current_user = request.user` y opcionalmente `instance._motivo_cambio_estado = '...'` antes de `save()` para registrar el responsable en `HistorialEstadoProyecto`.

**Señales de TareaChecklist** (en `projects/models.py`):
1. `notificar_sede_completada`: sincroniza estado Sede, sincroniza estado Proyecto (incluyendo fijación automática de `fecha_inicio` y `fecha_fin`), crea Notificaciones para admins/gerentes vía `bulk_create`.
2. `crear_jornada_al_completar_tarea`: si la tarea tiene exactamente 1 participante y hay contrato vigente, crea una `JornadaEmpleado` pendiente automáticamente.

**Empleado es el User model**: `AUTH_USER_MODEL = 'empleados.Empleado'`. Cargo: `request.user.cargo`.

## Settings Notes

- `AUTH_USER_MODEL = 'empleados.Empleado'`
- `LOGIN_URL = '/signin/'`, `LOGIN_REDIRECT_URL = '/dashboard/'`, `LOGOUT_REDIRECT_URL = '/'`
- `LANGUAGE_CODE = 'es'`, `TIME_ZONE = 'America/La_Paz'`
- Session: `SESSION_COOKIE_AGE = 1800` (30 min), `SESSION_SAVE_EVERY_REQUEST = True`, `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`
- `CSRF_FAILURE_VIEW = 'projects.views.csrf_failure'` — redirige al login con mensaje de sesión expirada
- `MEDIA_URL = '/media/'`, `MEDIA_ROOT = BASE_DIR / 'media'`
- Templates dirs: `BASE_DIR / 'templates'`, `BASE_DIR / 'empleados' / 'templates'`, `BASE_DIR / 'projects' / 'templates'`; además `APP_DIRS = True`
- Password validators customizados: `UppercaseValidator`, `LowercaseValidator`, `NumberValidator` (en `projects/validators.py`), mínimo 8 caracteres
- DB: SQLite (dev). PostgreSQL comentado con `dj_database_url`

## URL Structure

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
/proyectos/planificacion/                        → planificacion_gantt (AsignacionProyecto)
/proyectos/calendario/                           → calendario_equipo (jornadas del equipo)
/proyectos/reporte/
/proyectos/<id>/
/proyectos/<id>/ver/
/proyectos/<id>/acta-entrega/                    → project_finalizacion_pdf
/proyectos/<id>/eliminar/                        → hard delete
/proyectos/<id>/desactivar/
/proyectos/<id>/garantia/crear/                  → garantia_crear_manual

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
/proyectos/<id>/equipo/<id_employee>/cronograma/   → editar AsignacionProyecto

# Contratos de proyecto
/proyectos/<id>/contrato-proyecto/nuevo/
/contratos/proyecto/<id>/
/contratos/proyecto/<id>/desactivar/

# Clientes
/clientes/, /clientes/nuevo/, /clientes/<id>/, /clientes/<id>/ver/, /clientes/<id>/desactivar/
/clientes/ajax/nuevo/                            → create_cliente_ajax

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
/pagos/<id>/confirmar/                           → confirmar_pago_proyecto
/pagos/filtrar/                                  → AJAX filter por nombre de proyecto
/pagos/analisis/

# Garantías post-instalación
/proyectos/<id>/garantia/crear/                  → creación manual
/garantias/
/garantias/<id>/
/garantias/<id>/incidencias/nueva/
/garantias/incidencias/<id>/
/garantias/incidencias/<id>/desactivar/
/mis-reparaciones/                               → instalador/técnico: incidencias asignadas

# Empleados (empleados/urls.py)
/empleados/, /empleados/nuevo/, /empleados/carga/, /empleados/reporte/
/empleados/<id>/, /empleados/<id>/ver/, /empleados/<id>/desactivar/, /empleados/<id>/habilitar/
/empleados/carga/aprobar-todas/                  → bulk approve jornadas (aprobar_todas_jornadas)
/mi-trabajo/                                     → instalador_dashboard
/mis-cobros/                                     → mis_pagos_view

# Contratos de empleado (empleados/urls.py)
/empleados/<id>/contratos/nuevo/
/contratos/empleado/<id>/
/contratos/empleado/<id>/desactivar/
/contratos/empleado/<id>/pdf/

# Jornadas (empleados/urls.py)
/contratos/empleado/<id>/jornadas/nueva/
/jornadas/<id>/
/jornadas/<id>/eliminar/
/jornadas/<id>/aprobar/
/jornadas/<id>/rechazar/
/proyectos/<id>/jornadas/revision/               → revisar_jornadas_proyecto

# Pagos a empleados (empleados/urls.py)
/pagos-empleados/
/contratos/empleado/<id>/pagos/nuevo/
/pagos-empleado/<id>/
/pagos-empleado/<id>/confirmar/                  → confirmar_pago_empleado
/pagos-empleado/<id>/desactivar/

# Inventario (inventario/urls.py)
/proveedores/, /proveedores/nuevo/, /proveedores/<id>/, /proveedores/<id>/desactivar/
/proveedores/ajax/nuevo/                         → create_proveedor_ajax
/insumos/, /insumos/nuevo/, /insumos/<id>/, /insumos/<id>/ver/, /insumos/<id>/desactivar/
/insumos/ajax/nuevo/                             → create_insumo_ajax
/proyectos/<id>/insumos/nuevo/
/insumos-proyecto/<id>/
/insumos-proyecto/<id>/eliminar/
/insumos-proyecto/<id>/qr/                       → definida en root urls.py, no en inventario/urls.py
/compras/, /compras/nueva/, /compras/<id>/, /compras/<id>/desactivar/
/inventario/reporte/
```

## Diagrams

`docs/` — diagramas UWE en PlantUML (`.puml`). Requieren PlantUML instalado para renderizar.

Raíz del proyecto:
- `uc_*.puml` — diagramas de casos de uso por módulo
- `diagrama_conceptual.puml` — diagrama conceptual
- `diagrama_contenido.md` — diagrama de contenido (activo)
- `*.mmd` — diagramas Mermaid (se renderizan en [mermaid.live](https://mermaid.live))
- `uwe_generator.py` — script que parsea modelos y genera archivos `.mmd`
