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

    # Contratos de Empleados
    path('projects/<int:id_project>/contratos/empleado/nuevo/', views.create_contrato_empleado, name='create_contrato_empleado'),
    path('contratos/empleado/<int:id_contrato>/', views.contrato_empleado_detail, name='contrato_empleado_detail'),
    path('contratos/empleado/<int:id_contrato>/deactivate/', views.deactivate_contrato_empleado, name='contrato_empleado_deactivate'),
    # Contrato del Proyecto
    path('projects/<int:id_project>/contrato-proyecto/nuevo/', views.create_contrato_proyecto, name='create_contrato_proyecto'),
    path('contratos/proyecto/<int:id_contrato>/', views.contrato_proyecto_detail, name='contrato_proyecto_detail'),
    path('contratos/proyecto/<int:id_contrato>/deactivate/', views.deactivate_contrato_proyecto, name='contrato_proyecto_deactivate'),

    # Employees
    path('employees/', views.employees, name='employees'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/<int:id_employee>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:id_employee>/view/', views.employee_view, name='employee_view'),
    path('employees/<int:id_employee>/deactivate/', views.deactivate_employee, name='employee_deactivate'),

    # clientes
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/nuevo/', views.create_cliente, name='create_cliente'),
    path('clientes/<int:id_cliente>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:id_cliente>/ver/', views.cliente_view, name='cliente_view'),
    path('clientes/<int:id_cliente>/deactivate/', views.deactivate_cliente, name='cliente_deactivate'),

    # Analysis y Reporte de proyectos
    path('reporte-analisis/', views.project_analysis, name='project_analysis'),
    path('project_report/', views.project_report, name='project_report'),

    # Módulo Inventario
    path('', include('inventario.urls')),

    # Módulo Pagos
    path('', include('pagos.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
