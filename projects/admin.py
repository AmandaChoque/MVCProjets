from django.contrib import admin
from projects.models import (
    Proyecto, HistorialPresupuesto, Cliente, Progreso, Pago,
)
from empleados.models import PagoEmpleado
from inventario.models import Proveedor, Insumo, Compra


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')
    list_display = ('codigo', 'nombre', 'estado_proyecto', 'tipo_proyecto', 'estado_pago', 'monto_total', 'activo', 'creado_por')
    list_filter = ('activo', 'estado_proyecto', 'tipo_proyecto', 'estado_pago')
    search_fields = ('nombre', 'codigo', 'cliente__nombre', 'cliente__apellido_paterno')
    ordering = ('-created',)
    list_per_page = 20


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'rol_contacto', 'nit_ci', 'tipo_contratante', 'telefono', 'activo')
    list_filter = ('activo', 'tipo_contratante')
    search_fields = ('nombre', 'apellido_paterno', 'nit_ci', 'rol_contacto')
    ordering = ('apellido_paterno', 'nombre')
    list_per_page = 20

    def get_queryset(self, request):
        return Cliente.all_objects.all()


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'monto', 'fecha', 'tipo_pago', 'numero_referencia', 'proyecto', 'activo', 'created')
    list_filter = ('activo', 'tipo_pago')
    search_fields = ('proyecto__nombre', 'proyecto__codigo')
    ordering = ('-fecha',)
    list_per_page = 20



@admin.register(HistorialPresupuesto)
class HistorialPresupuestoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'monto_anterior', 'monto_actual', 'motivo_cambio', 'fecha_modificacion')
    list_filter = ('proyecto',)
    search_fields = ('proyecto__nombre', 'motivo_cambio')
    ordering = ('-fecha_modificacion',)
    list_per_page = 20


@admin.register(Progreso)
class ProgresoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'fecha', 'porcentaje', 'descripcion', 'created')
    list_filter = ('proyecto',)
    search_fields = ('proyecto__nombre', 'descripcion')
    ordering = ('-fecha',)
    list_per_page = 20



@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rubro', 'telefono', 'nit', 'encargado_nombre', 'activo', 'created')
    list_filter = ('activo',)
    search_fields = ('nombre', 'rubro', 'nit')
    ordering = ('nombre',)
    list_per_page = 20
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'categoria', 'ultimo_precio_compra', 'stock', 'activo', 'created')
    list_filter = ('activo', 'categoria')
    search_fields = ('nombre', 'marca')
    ordering = ('categoria', 'nombre')
    list_per_page = 20
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('insumo', 'proveedor', 'cantidad', 'costo_total', 'fecha', 'numero_factura', 'activo', 'created')
    list_filter = ('activo',)
    search_fields = ('insumo__nombre', 'proveedor__nombre', 'numero_factura')
    ordering = ('-fecha',)
    list_per_page = 20
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(PagoEmpleado)
class PagoEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'monto', 'fecha', 'concepto', 'tipo_pago', 'activo', 'created')
    list_filter = ('activo',)
    search_fields = ('contrato__empleado__nombre', 'concepto')
    ordering = ('-fecha',)
    list_per_page = 20
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')
