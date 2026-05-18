from django.urls import path
from . import views

urlpatterns = [
    # Empleados
    path('empleados/', views.employees, name='employees'),
    path('empleados/nuevo/', views.create_employee, name='create_employee'),
    path('empleados/carga/', views.employee_workload, name='employee_workload'),
    path('empleados/carga/aprobar-todas/', views.aprobar_todas_jornadas, name='aprobar_todas_jornadas'),
    path('empleados/reporte/', views.employee_report, name='employee_report'),
    path('empleados/<int:id_employee>/', views.employee_detail, name='employee_detail'),
    path('empleados/<int:id_employee>/ver/', views.employee_view, name='employee_view'),
    path('empleados/<int:id_employee>/desactivar/', views.deactivate_employee, name='employee_deactivate'),
    path('empleados/<int:id_employee>/habilitar/', views.reactivate_employee, name='employee_reactivate'),

    # Contratos de empleado
    path('empleados/<int:id_employee>/contratos/nuevo/', views.create_contrato_from_employee, name='create_contrato_from_employee'),
    path('contratos/empleado/<int:id_contrato>/', views.contrato_empleado_detail, name='contrato_empleado_detail'),
    path('contratos/empleado/<int:id_contrato>/desactivar/', views.deactivate_contrato_empleado, name='contrato_empleado_deactivate'),
    path('contratos/empleado/<int:id_contrato>/pdf/', views.contrato_empleado_pdf, name='contrato_empleado_pdf'),

    # Jornadas
    path('contratos/empleado/<int:id_contrato>/jornadas/nueva/', views.create_jornada, name='create_jornada'),
    path('jornadas/<int:id_jornada>/', views.jornada_detail, name='jornada_detail'),
    path('jornadas/<int:id_jornada>/eliminar/', views.deactivate_jornada, name='deactivate_jornada'),
    path('jornadas/<int:id_jornada>/aprobar/', views.aprobar_jornada, name='aprobar_jornada'),
    path('jornadas/<int:id_jornada>/rechazar/', views.rechazar_jornada, name='rechazar_jornada'),
    path('proyectos/<int:id_proyecto>/jornadas/revision/', views.revisar_jornadas_proyecto, name='revisar_jornadas_proyecto'),

    # Dashboard instalador
    path('mi-trabajo/', views.instalador_dashboard, name='instalador_dashboard'),
    path('mis-cobros/', views.mis_pagos_view, name='mis_pagos_view'),

    # Pagos a empleados
    path('pagos-empleados/', views.pagos_empleados_list, name='pagos_empleados_list'),
    path('contratos/empleado/<int:id_contrato>/pagos/nuevo/', views.create_pago_empleado, name='create_pago_empleado'),
    path('pagos-empleado/<int:id_pago>/', views.pago_empleado_detail, name='pago_empleado_detail'),
    path('pagos-empleado/<int:id_pago>/desactivar/', views.deactivate_pago_empleado, name='pago_empleado_deactivate'),
    path('pagos-empleado/<int:id_pago>/confirmar/', views.confirmar_pago_empleado, name='confirmar_pago_empleado'),
]
