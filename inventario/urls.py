from django.urls import path
from . import views

urlpatterns = [
    # Proveedores
    path('proveedores/', views.proveedores, name='proveedores'),
    path('proveedores/nuevo/', views.create_proveedor, name='create_proveedor'),
    path('proveedores/<int:id_proveedor>/', views.proveedor_detail, name='proveedor_detail'),
    path('proveedores/<int:id_proveedor>/desactivar/', views.deactivate_proveedor, name='proveedor_deactivate'),

    # Insumos
    path('insumos/', views.insumos, name='insumos'),
    path('insumos/nuevo/', views.create_insumo, name='create_insumo'),
    path('insumos/<int:id_insumo>/', views.insumo_detail, name='insumo_detail'),
    path('insumos/<int:id_insumo>/ver/', views.insumo_view, name='insumo_view'),
    path('insumos/<int:id_insumo>/desactivar/', views.deactivate_insumo, name='insumo_deactivate'),

    # Requiere (insumos por proyecto)
    path('proyectos/<int:id_project>/insumos/nuevo/', views.create_requiere, name='create_requiere'),
    path('insumos-proyecto/<int:id_requiere>/', views.requiere_detail, name='requiere_detail'),
    path('insumos-proyecto/<int:id_requiere>/eliminar/', views.deactivate_requiere, name='requiere_deactivate'),

    # Compras
    path('compras/', views.compras, name='compras'),
    path('compras/nueva/', views.create_compra, name='create_compra'),
    path('compras/<int:id_compra>/', views.compra_detail, name='compra_detail'),
    path('compras/<int:id_compra>/desactivar/', views.deactivate_compra, name='compra_deactivate'),

    path('inventario/reporte/', views.inventario_report, name='inventario_report'),
]
