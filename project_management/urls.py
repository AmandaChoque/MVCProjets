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
from django.urls import path
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

    # Payments
    path("payments/", views.payment_list, name="payments"),
    path("payments/create/", views.create_payment, name="create_payment"),
    path('payments/<int:id_payment>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:id_payment>/view/', views.payment_view, name='payment_view'),
    path('payments/<int:id_payment>/deactivate/', views.deactivate_payment, name='payment_deactivate'),

    # Public Entities
    path('public_entities/', views.public_entities, name='public_entities'),
    path('public_entities/<int:id_public_entity>/', views.public_entity_detail, name='public_entity_detail'),
    path('public_entities/<int:id_public_entity>/deactivate/', views.deactivate_public_entity, name='public_entity_deactivate'),
    path('public_entity/create/', views.create_public_entity, name='create_public_entity'),

    # Proposals
    path('proposals/', views.proposals, name='proposals'),
    path('proposals/<int:id_proposal>/', views.proposal_detail, name='proposal_detail'),
    path('proposals/<int:id_proposal>/deactivate/', views.deactivate_proposal, name='proposal_deactivate'),
    path('proposal/create/', views.create_proposal, name='create_proposal'),


    # clientes
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/nuevo/', views.create_cliente, name='create_cliente'),
    path('clientes/<int:id_cliente>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:id_cliente>/ver/', views.cliente_view, name='cliente_view'),
    path('clientes/<int:id_cliente>/deactivate/', views.deactivate_cliente, name='cliente_deactivate'),

    # Analysis y Reporte
    path('reporte-analisis/', views.project_analysis, name='project_analysis'),
    path('project_report/', views.project_report, name='project_report'),
    path('payments/filter/', views.filter_payments_by_project_name, name='filter_payments_by_project_name'),
    path('payment-analysis/', views.payment_analysis, name='payment_analysis'),

    # Proveedores
    path('proveedores/', views.proveedores, name='proveedores'),
    path('proveedores/nuevo/', views.create_proveedor, name='create_proveedor'),
    path('proveedores/<int:id_proveedor>/', views.proveedor_detail, name='proveedor_detail'),
    path('proveedores/<int:id_proveedor>/deactivate/', views.deactivate_proveedor, name='proveedor_deactivate'),

    # Insumos
    path('insumos/', views.insumos, name='insumos'),
    path('insumos/nuevo/', views.create_insumo, name='create_insumo'),
    path('insumos/<int:id_insumo>/', views.insumo_detail, name='insumo_detail'),
    path('insumos/<int:id_insumo>/deactivate/', views.deactivate_insumo, name='insumo_deactivate'),

    # Requiere
    path('projects/<int:id_project>/insumos/nuevo/', views.create_requiere, name='create_requiere'),
    path('insumos-proyecto/<int:id_requiere>/', views.requiere_detail, name='requiere_detail'),
    path('insumos-proyecto/<int:id_requiere>/eliminar/', views.deactivate_requiere, name='requiere_deactivate'),

    # Compras
    path('compras/', views.compras, name='compras'),
    path('compras/nueva/', views.create_realizar, name='create_realizar'),
    path('compras/<int:id_realizar>/', views.realizar_detail, name='realizar_detail'),
    path('compras/<int:id_realizar>/deactivate/', views.deactivate_realizar, name='realizar_deactivate'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
