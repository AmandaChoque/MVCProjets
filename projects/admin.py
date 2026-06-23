from django.contrib import admin
from projects.models import (
    Proyecto, HistorialPresupuesto, HistorialEstadoProyecto, Cliente,
    PagoProyecto, ContratoProyecto, PlantillaTarea, Sede, TareaChecklist,
    SubtareaChecklist, FotoSede, Notificacion, Garantia, IncidenciaGarantia,
    AsignacionProyecto,
)
from empleados.models import PagoEmpleado
from inventario.models import Proveedor, Insumo, Compra, Requiere, RequiereLote


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


@admin.register(PagoProyecto)
class PagoProyectoAdmin(admin.ModelAdmin):
    list_display = ('id', 'monto', 'fecha', 'tipo_pago', 'numero_referencia', 'proyecto', 'activo', 'created')
    list_filter = ('activo', 'tipo_pago')
    search_fields = ('proyecto__nombre', 'proyecto__codigo')
    ordering = ('-fecha',)
    list_per_page = 20



@admin.register(ContratoProyecto)
class ContratoProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'monto_acordado', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('proyecto__nombre',)
    ordering = ('-created',)
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(HistorialPresupuesto)
class HistorialContratoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'monto_anterior', 'monto_actual', 'motivo_cambio', 'fecha_modificacion')
    list_filter = ('proyecto',)
    search_fields = ('proyecto__nombre', 'motivo_cambio')
    ordering = ('-fecha_modificacion',)
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


@admin.register(HistorialEstadoProyecto)
class HistorialEstadoProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'estado_anterior', 'estado_nuevo', 'cambiado_por', 'fecha')
    list_filter = ('estado_nuevo',)
    search_fields = ('proyecto__nombre',)
    ordering = ('-fecha',)
    list_per_page = 20


@admin.register(AsignacionProyecto)
class AsignacionProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'empleado', 'fecha_inicio_plan', 'fecha_fin_plan', 'dias_planificados', 'activo')
    list_filter = ('activo',)
    search_fields = ('proyecto__nombre', 'empleado__nombre')
    ordering = ('-created',)
    list_per_page = 20


@admin.register(PlantillaTarea)
class PlantillaTareaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activo')
    list_filter = ('activo', 'tipo')
    search_fields = ('nombre',)


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proyecto', 'direccion', 'estado', 'activo')
    list_filter = ('activo', 'estado')
    search_fields = ('nombre', 'direccion', 'proyecto__nombre')
    ordering = ('proyecto', 'nombre')
    list_per_page = 20


@admin.register(TareaChecklist)
class TareaChecklistAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'sede', 'completado', 'completado_por', 'fecha_completado', 'activo')
    list_filter = ('activo', 'completado')
    search_fields = ('descripcion', 'sede__nombre', 'sede__proyecto__nombre')
    ordering = ('sede', 'orden')
    list_per_page = 20


@admin.register(SubtareaChecklist)
class SubtareaChecklistAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'tarea', 'completado', 'completado_por', 'activo')
    list_filter = ('activo', 'completado')
    search_fields = ('descripcion',)
    list_per_page = 20


@admin.register(FotoSede)
class FotoSedeAdmin(admin.ModelAdmin):
    list_display = ('sede', 'descripcion', 'subida_por', 'created')
    search_fields = ('sede__nombre', 'descripcion')
    ordering = ('-created',)
    list_per_page = 20


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'tipo', 'mensaje', 'leida', 'fecha')
    list_filter = ('tipo', 'leida')
    search_fields = ('mensaje', 'destinatario__nombre')
    ordering = ('-fecha',)
    list_per_page = 20


@admin.register(Garantia)
class GarantiaAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'fecha_inicio', 'fecha_vencimiento')
    search_fields = ('contrato__proyecto__nombre',)
    ordering = ('-fecha_inicio',)
    list_per_page = 20


@admin.register(IncidenciaGarantia)
class IncidenciaGarantiaAdmin(admin.ModelAdmin):
    list_display = ('garantia', 'descripcion', 'estado', 'fecha_reporte', 'costo_reparacion', 'activo')
    list_filter = ('activo', 'estado')
    search_fields = ('descripcion',)
    ordering = ('-fecha_reporte',)
    list_per_page = 20


@admin.register(Requiere)
class RequiereAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'insumo', 'cantidad', 'activo')
    list_filter = ('activo',)
    search_fields = ('proyecto__nombre', 'insumo__nombre')
    list_per_page = 20


@admin.register(RequiereLote)
class RequiereLoteAdmin(admin.ModelAdmin):
    list_display = ('requiere', 'compra', 'cantidad', 'activo')
    list_filter = ('activo',)
    list_per_page = 20


@admin.register(PagoEmpleado)
class PagoEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'monto', 'fecha', 'concepto', 'estado', 'activo', 'created')
    list_filter = ('activo', 'estado', 'concepto')
    search_fields = ('contrato__empleado__nombre', 'concepto')
    ordering = ('-fecha',)
    list_per_page = 20
    readonly_fields = ('created', 'updated_at', 'deleted_at', 'deleted_by')
