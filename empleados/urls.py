from django.urls import path
from . import views

urlpatterns = [
    # Empleados
    path('employees/', views.employees, name='employees'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/carga/', views.employee_workload, name='employee_workload'),
    path('employees/<int:id_employee>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:id_employee>/view/', views.employee_view, name='employee_view'),
    path('employees/<int:id_employee>/deactivate/', views.deactivate_employee, name='employee_deactivate'),

    # Contratos de empleado
    path('employees/<int:id_employee>/contratos/nuevo/', views.create_contrato_from_employee, name='create_contrato_from_employee'),
    path('contratos/empleado/<int:id_contrato>/', views.contrato_empleado_detail, name='contrato_empleado_detail'),
    path('contratos/empleado/<int:id_contrato>/deactivate/', views.deactivate_contrato_empleado, name='contrato_empleado_deactivate'),

    # Jornadas
    path('contratos/empleado/<int:id_contrato>/jornadas/nueva/', views.create_jornada, name='create_jornada'),
    path('jornadas/<int:id_jornada>/', views.jornada_detail, name='jornada_detail'),
    path('jornadas/<int:id_jornada>/eliminar/', views.deactivate_jornada, name='deactivate_jornada'),

    # Dashboard instalador
    path('mi-trabajo/', views.instalador_dashboard, name='instalador_dashboard'),

    # Pagos a empleados
    path('pagos-empleados/',                                         views.pagos_empleados_list,      name='pagos_empleados_list'),
    path('contratos/empleado/<int:id_contrato>/pagos/nuevo/',        views.create_pago_empleado,      name='create_pago_empleado'),
    path('pagos-empleado/<int:id_pago>/',                            views.pago_empleado_detail,      name='pago_empleado_detail'),
    path('pagos-empleado/<int:id_pago>/deactivate/',                 views.deactivate_pago_empleado,  name='pago_empleado_deactivate'),
]
