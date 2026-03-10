from django.contrib import admin
from projects.models import Proyecto, Empleado, HistorialPago, Pago, Propuesta, EntidadPublica, Cliente


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'updated_at', 'deleted_at')
    list_display = ('codigo', 'nombre', 'estado_proyecto', 'tipo_proyecto', 'estado_pago', 'monto_total', 'activo', 'fecha_inicio', 'user')
    list_filter = ('activo', 'estado_proyecto', 'tipo_proyecto', 'estado_pago')
    search_fields = ('nombre', 'codigo', 'cliente__nombre', 'cliente__apellido_paterno')
    ordering = ('-created',)
    list_per_page = 20


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'apellido_materno', 'cargo', 'carnet_identidad', 'numero_celular', 'activo')
    list_filter = ('activo', 'cargo')
    search_fields = ('nombre', 'apellido_paterno', 'carnet_identidad')
    ordering = ('apellido_paterno', 'nombre')
    list_per_page = 20


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'cargo', 'nit_ci', 'tipo_contratante', 'telefono', 'activo')
    list_filter = ('activo', 'tipo_contratante')
    search_fields = ('nombre', 'apellido_paterno', 'nit_ci', 'cargo')
    ordering = ('apellido_paterno', 'nombre')
    list_per_page = 20

    def get_queryset(self, request):
        return Cliente.all_objects.all()


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'monto', 'fecha', 'estado', 'tipo_pago', 'proyecto', 'activo', 'created')
    list_filter = ('activo', 'estado', 'tipo_pago')
    search_fields = ('proyecto__nombre', 'proyecto__codigo')
    ordering = ('-fecha',)
    list_per_page = 20


@admin.register(EntidadPublica)
class EntidadPublicaAdmin(admin.ModelAdmin):
    list_display = ('nombre_entidad', 'representante_legal', 'contacto', 'direccion', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre_entidad', 'representante_legal', 'contacto')
    ordering = ('nombre_entidad',)
    list_per_page = 20


@admin.register(Propuesta)
class PropuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'entidad_publica', 'fecha_presentacion', 'monto_presupuesto', 'activo', 'created')
    list_filter = ('activo', 'entidad_publica')
    search_fields = ('entidad_publica__nombre_entidad', 'requisitos')
    ordering = ('-fecha_presentacion',)
    list_per_page = 20


@admin.register(HistorialPago)
class HistorialPagoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'monto_anterior', 'monto_actual', 'motivo_cambio', 'fecha_modificacion')
    list_filter = ('proyecto',)
    search_fields = ('proyecto__nombre', 'motivo_cambio')
    ordering = ('-fecha_modificacion',)
    list_per_page = 20
