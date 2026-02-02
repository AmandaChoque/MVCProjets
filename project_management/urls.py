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
from projects import views






urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_home, name='dashboard'),
    path('admin/', admin.site.urls),
    # path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='signout'),
    path('signin/', views.signin, name='signin'),
    
    # Proyects
    path('projects/', views.projects, name='projects'),
    path('projects_completed/', views.projects_completed, name='projects_completed'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:id_project>/', views.project_detail, name='project_detail'),
    path('projects/<int:id_project>/complete/', views.project_complete, name='project_complete'),
    path('projects/<int:id_project>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:id_project>/deactivate/', views.deactivate_project, name='project_deactivate'),
    
    # Employees
    path('employees/', views.employees, name='employees'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/<int:id_employee>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:id_employee>/deactivate/', views.deactivate_employee, name='employee_deactivate'),

    # Payments
    path("payments/", views.payment_list, name="payments"),
    path("payments/create/", views.create_payment, name="create_payment"),
    path('payments/<int:id_payment>/', views.payment_detail, name='payment_detail'),
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
    path('clientes/<int:id_cliente>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:id_cliente>/deactivate/', views.deactivate_cliente, name='cliente_deactivate'),
    path('cliente/create/', views.create_cliente, name='create_cliente'),

    # Analysis y Reporte
    path('reporte-analisis/', views.project_analysis, name='project_analysis'),
    path('project_report/', views.project_report, name='project_report'),
    path('payments/filter/', views.filter_payments_by_project_name, name='filter_payments_by_project_name'),
    path('payment-analysis/', views.payment_analysis, name='payment_analysis'),

    # path('project/<int:id_project>/payments/', views.filter_payments_by_project, name='filter_payments_by_project'),
    # path('project/<int:project_id>/payments/', views.project_payment_history, name='project_payment_history'),
    # path('project/<int:project_id>/payments/pdf/', views.generate_payment_pdf, name='generate_payment_pdf'),
    # path('project-analysis/', project_analysis, name='project_analysis'),
]
