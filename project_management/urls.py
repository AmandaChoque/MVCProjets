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
    path('dashboard/', views.dashboard_home, name='dashboard'),
    path('admin/', admin.site.urls),
    # path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('signout/', views.signout, name='signout'),
    path('signin/', views.signin, name='signin'),
    path('extend-session/', views.extend_session, name='extend_session'),
    path('cambiar-contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),
    
    # Proyects
    path('projects/', views.projects, name='projects'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:id_project>/', views.project_detail, name='project_detail'),
    path('projects/<int:id_project>/view/', views.project_view, name='project_view'),
    path('projects/<int:id_project>/complete/', views.project_complete, name='project_complete'),
    path('projects/<int:id_project>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:id_project>/deactivate/', views.deactivate_project, name='project_deactivate'),
    path('projects/<int:id_project>/progreso/nuevo/', views.create_progreso, name='create_progreso'),
    path('progreso/<int:id_progreso>/', views.progreso_detail, name='progreso_detail'),
    path('progreso/<int:id_progreso>/eliminar/', views.deactivate_progreso, name='deactivate_progreso'),

    # Sedes de Instalación
    path('projects/<int:id_project>/sedes/nueva/', views.sede_create, name='sede_create'),
    path('sedes/<int:id_sede>/', views.sede_detail, name='sede_detail'),
    path('sedes/<int:id_sede>/ver/', views.sede_view, name='sede_view'),
    path('sedes/<int:id_sede>/deactivate/', views.sede_deactivate, name='sede_deactivate'),
    # Checklist de tareas
    path('sedes/<int:id_sede>/tareas/nueva/', views.tarea_create, name='tarea_create'),
    path('tareas/<int:id_tarea>/toggle/', views.tarea_toggle, name='tarea_toggle'),
    path('tareas/<int:id_tarea>/eliminar/', views.tarea_delete, name='tarea_delete'),
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
    path('projects/<int:id_project>/equipo/agregar/', views.equipo_add, name='equipo_add'),
    path('projects/<int:id_project>/equipo/<int:id_employee>/remover/', views.equipo_remove, name='equipo_remove'),
    # Contrato del Proyecto
    path('projects/<int:id_project>/contrato-proyecto/nuevo/', views.create_contrato_proyecto, name='create_contrato_proyecto'),
    path('contratos/proyecto/<int:id_contrato>/', views.contrato_proyecto_detail, name='contrato_proyecto_detail'),
    path('contratos/proyecto/<int:id_contrato>/deactivate/', views.deactivate_contrato_proyecto, name='contrato_proyecto_deactivate'),

    # clientes
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/nuevo/', views.create_cliente, name='create_cliente'),
    path('clientes/<int:id_cliente>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:id_cliente>/ver/', views.cliente_view, name='cliente_view'),
    path('clientes/<int:id_cliente>/deactivate/', views.deactivate_cliente, name='cliente_deactivate'),

    # Analysis y Reporte de proyectos
    path('reporte-analisis/', views.project_analysis, name='project_analysis'),
    path('project_report/', views.project_report, name='project_report'),

    # Módulo Empleados
    path('', include('empleados.urls')),

    # Módulo Inventario
    path('', include('inventario.urls')),

    # Pagos del cliente (proyecto)
    path('payments/',                                views.payment_list,                      name='payments'),
    path('payments/create/',                         views.create_payment,                    name='create_payment'),
    path('payments/<int:id_payment>/',               views.payment_detail,                    name='payment_detail'),
    path('payments/<int:id_payment>/view/',          views.payment_view,                      name='payment_view'),
    path('payments/<int:id_payment>/deactivate/',    views.deactivate_payment,                name='payment_deactivate'),
    path('payments/filter/',                         views.filter_payments_by_project_name,   name='filter_payments_by_project_name'),
    path('payment-analysis/',                        views.payment_analysis,                  name='payment_analysis'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
