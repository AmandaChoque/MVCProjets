from django.urls import path
from . import views

urlpatterns = [
    # Pagos del cliente
    path('payments/',                            views.payment_list,          name='payments'),
    path('payments/create/',                     views.create_payment,        name='create_payment'),
    path('payments/<int:id_payment>/',           views.payment_detail,        name='payment_detail'),
    path('payments/<int:id_payment>/view/',      views.payment_view,          name='payment_view'),
    path('payments/<int:id_payment>/deactivate/', views.deactivate_payment,   name='payment_deactivate'),
    path('payments/filter/',                     views.filter_payments_by_project_name, name='filter_payments_by_project_name'),

    # Análisis de pagos
    path('payment-analysis/',                    views.payment_analysis,      name='payment_analysis'),

    # Pagos a empleados
    path('pagos-empleados/',                     views.pagos_empleados_list,  name='pagos_empleados_list'),
    path('contratos/empleado/<int:id_contrato>/pagos/nuevo/', views.create_pago_empleado,  name='create_pago_empleado'),
    path('pagos-empleado/<int:id_pago>/',        views.pago_empleado_detail,  name='pago_empleado_detail'),
    path('pagos-empleado/<int:id_pago>/deactivate/', views.deactivate_pago_empleado, name='pago_empleado_deactivate'),
]
