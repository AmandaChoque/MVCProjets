"""
URL configuration for project_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from projects import views


urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('consulta-proyecto/', views.consulta_proyecto, name='consulta_proyecto'),
    path('dashboard/', views.dashboard_home, name='dashboard'),
    path('admin/', admin.site.urls),
    path('signup/', views.signup, name='signup'),
    path('signout/', views.signout, name='signout'),
    path('signin/', views.signin, name='signin'),
    path('extend-session/', views.extend_session, name='extend_session'),
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),

    # Proyectos
    path('proyectos/', views.projects, name='projects'),
    path('proyectos/nuevo/', views.create_project, name='create_project'),
    path('proyectos/analisis/', views.project_analysis, name='project_analysis'),
    path('proyectos/seguimiento/', views.seguimiento_avance, name='seguimiento_avance'),
    path('proyectos/reporte/', views.project_report, name='project_report'),
    path('proyectos/financiero/', views.analisis_financiero, name='analisis_financiero'),
    path('proyectos/planificacion/', views.planificacion_gantt, name='planificacion_gantt'),
    path('proyectos/calendario/', views.calendario_equipo, name='calendario_equipo'),
    path('proyectos/<int:id_project>/', views.project_detail, name='project_detail'),
    path('proyectos/<int:id_project>/ver/', views.project_view, name='project_view'),
    path('proyectos/<int:id_project>/acta-entrega/', views.project_finalizacion_pdf, name='project_finalizacion_pdf'),
path('proyectos/<int:id_project>/eliminar/', views.project_delete, name='project_delete'),
    path('proyectos/<int:id_project>/desactivar/', views.deactivate_project, name='project_deactivate'),

    # Sedes de Instalación
    path('proyectos/<int:id_project>/sedes/nueva/', views.sede_create, name='sede_create'),
    path('sedes/<int:id_sede>/', views.sede_detail, name='sede_detail'),
    path('sedes/<int:id_sede>/ver/', views.sede_view, name='sede_view'),
    path('sedes/<int:id_sede>/desactivar/', views.sede_deactivate, name='sede_deactivate'),

    # Checklist de tareas
    path('sedes/<int:id_sede>/tareas/nueva/', views.tarea_create, name='tarea_create'),
    path('tareas/<int:id_tarea>/alternar/', views.tarea_toggle, name='tarea_toggle'),
    path('tareas/<int:id_tarea>/participantes/', views.tarea_set_participantes, name='tarea_set_participantes'),
    path('tareas/<int:id_tarea>/editar/', views.tarea_edit, name='tarea_edit'),
    path('tareas/<int:id_tarea>/eliminar/', views.tarea_delete, name='tarea_delete'),
    path('tareas/<int:id_tarea>/subtareas/nueva/', views.subtarea_create, name='subtarea_create'),
    path('subtareas/<int:id_subtarea>/editar/', views.subtarea_edit, name='subtarea_edit'),
    path('subtareas/<int:id_subtarea>/alternar/', views.subtarea_toggle, name='subtarea_toggle'),
    path('subtareas/<int:id_subtarea>/eliminar/', views.subtarea_delete, name='subtarea_delete'),
    path('sedes/<int:id_sede>/tareas/reordenar/', views.tareas_reorder, name='tareas_reorder'),
    path('sedes/<int:id_sede>/aplicar-plantilla/', views.aplicar_plantilla_sede, name='aplicar_plantilla_sede'),

    # Fotos de sede
    path('sedes/<int:id_sede>/fotos/subir/', views.foto_upload, name='foto_upload'),
    path('fotos/<int:id_foto>/eliminar/', views.foto_delete, name='foto_delete'),

    # QR por insumo instalado
    path('insumos-proyecto/<int:id_requiere>/qr/', views.qr_insumo, name='qr_insumo'),

    # Notificaciones
    path('notificaciones/', views.notificaciones_list, name='notificaciones_list'),
    path('notificaciones/<int:id_notif>/leer/', views.notificacion_marcar_leida, name='notificacion_leer'),
    path('notificaciones/leer-todas/', views.notificaciones_marcar_todas, name='notificaciones_leer_todas'),

    # Equipo del Proyecto
    path('proyectos/<int:id_project>/equipo/agregar/', views.equipo_add, name='equipo_add'),
    path('proyectos/<int:id_project>/equipo/<int:id_employee>/remover/', views.equipo_remove, name='equipo_remove'),
    path('proyectos/<int:id_project>/equipo/<int:id_employee>/cronograma/', views.asignacion_edit, name='asignacion_edit'),

    # Contrato del Proyecto
    path('proyectos/<int:id_project>/contrato-proyecto/nuevo/', views.create_contrato_proyecto, name='create_contrato_proyecto'),
    path('contratos/proyecto/<int:id_contrato>/', views.contrato_proyecto_detail, name='contrato_proyecto_detail'),
    path('contratos/proyecto/<int:id_contrato>/desactivar/', views.deactivate_contrato_proyecto, name='contrato_proyecto_deactivate'),

    # Clientes
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/nuevo/', views.create_cliente, name='create_cliente'),
    path('clientes/ajax/nuevo/', views.create_cliente_ajax, name='create_cliente_ajax'),
    path('clientes/<int:id_cliente>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:id_cliente>/ver/', views.cliente_view, name='cliente_view'),
    path('clientes/<int:id_cliente>/desactivar/', views.deactivate_cliente, name='cliente_deactivate'),

    # Plantillas de tareas
    path('plantillas/', views.plantillas_list, name='plantillas_list'),
    path('plantillas/nueva/', views.plantilla_create, name='plantilla_create'),
    path('plantillas/<int:id_plantilla>/', views.plantilla_detail, name='plantilla_detail'),
    path('plantillas/<int:id_plantilla>/desactivar/', views.plantilla_deactivate, name='plantilla_deactivate'),
    path('plantillas/<int:id_plantilla>/items/nuevo/', views.item_plantilla_create, name='item_plantilla_create'),
    path('plantillas/items/<int:id_item>/eliminar/', views.item_plantilla_delete, name='item_plantilla_delete'),
    path('plantillas/items/<int:id_item>/editar/', views.item_plantilla_edit, name='item_plantilla_edit'),
    path('plantillas/items/<int:id_item>/subitems/nuevo/', views.subitem_plantilla_create, name='subitem_plantilla_create'),
    path('plantillas/subitems/<int:id_subitem>/editar/', views.subitem_plantilla_edit, name='subitem_plantilla_edit'),
    path('plantillas/subitems/<int:id_subitem>/eliminar/', views.subitem_plantilla_delete, name='subitem_plantilla_delete'),
    path('plantillas/<int:id_plantilla>/items/reordenar/', views.items_plantilla_reorder, name='items_plantilla_reorder'),

    # Módulo Empleados
    path('', include('empleados.urls')),

    # Módulo Inventario
    path('', include('inventario.urls')),

    # Garantías post-instalación
    path('proyectos/<int:id_project>/garantia/crear/', views.garantia_crear_manual, name='garantia_crear_manual'),
    path('garantias/', views.garantias_list, name='garantias_list'),
    path('garantias/<int:id_garantia>/', views.garantia_detail, name='garantia_detail'),
    path('garantias/<int:id_garantia>/incidencias/nueva/', views.incidencia_garantia_create, name='incidencia_garantia_create'),
    path('garantias/incidencias/<int:id_incidencia>/', views.incidencia_garantia_detail, name='incidencia_garantia_detail'),
    path('garantias/incidencias/<int:id_incidencia>/desactivar/', views.incidencia_garantia_deactivate, name='incidencia_garantia_deactivate'),
    path('mis-reparaciones/', views.mis_reparaciones, name='mis_reparaciones'),

    # Pagos del cliente al proyecto
    path('pagos/', views.payment_list, name='payments'),
    path('pagos/nuevo/', views.create_payment, name='create_payment'),
    path('pagos/filtrar/', views.filter_payments_by_project_name, name='filter_payments_by_project_name'),
    path('pagos/analisis/', views.payment_analysis, name='payment_analysis'),
    path('pagos/<int:id_payment>/', views.payment_detail, name='payment_detail'),
    path('pagos/<int:id_payment>/ver/', views.payment_view, name='payment_view'),
    path('pagos/<int:id_payment>/desactivar/', views.deactivate_payment, name='payment_deactivate'),
    path('pagos/<int:id_payment>/confirmar/', views.confirmar_pago_proyecto, name='confirmar_pago_proyecto'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
