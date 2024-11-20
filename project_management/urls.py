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
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
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
    path('employees/<int:id_employee>/', views.employee_detail, name='employee_detail'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/<int:id_employee>/deactivate/', views.deactivate_employee, name='employee_deactivate'),


    # Historial de Pagos
    path('payment_histories/', views.payment_histories, name='payment_histories'),

    # # Payments
    path("payment/", views.PaymentListView.as_view(), name="list"),
    path("payment/create/", views.PaymentCreateView.as_view(), name="create"),
    # path('payments/<int:id_payment>/payments/', views.payment_list, name='payment_list'),
    # path('payments/<int:id_payment>/payments/create/', views.create_payment, name='create_payment'),


    # Analysis y Reporte
    path('reporte-analisis/', views.project_analysis, name='project_analysis'),
    path('project_report/', views.project_report, name='project_report'),
    # path('project-analysis/', project_analysis, name='project_analysis'),
]
