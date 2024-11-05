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
    path('projects/', views.projects, name='projects'),
    path('projects_completed/', views.projects_completed, name='projects_completed'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:id_project>/', views.project_detail, name='project_detail'),

    path('projects/<int:id_project>/complete/', views.project_complete, name='project_complete'),
    path('projects/<int:id_project>/delete/', views.project_delete, name='project_delete'),
    path('logout/', views.signout, name='signout'),
    path('signin/', views.signin, name='signin'),
    
    # Employees
    path('employees/', views.employees, name='employees'),
    path('employees/<int:id_employee>/', views.project_detail, name='employee_detail'),
    

    # Historial de Pagos
    path('payment_histories/', views.payment_histories, name='payment_histories'),

]
