from django.contrib import admin

from projects.models import Proyecto, Empleado, HistorialPago, Pago, Propuesta, EntidadPublica, Cliente

# Register your models here.
class ProyectoAdmin(admin.ModelAdmin):
    readonly_fields = ("created", )
    list_display = ('id', 'nombre','estado_pago','fecha_inicio','fecha_fin','estado_proyecto','tipo_proyecto', 'activo','created',
'updated_at',
'deleted_at', 'user')
    search_fields = ['nombre']
admin.site.register(Proyecto, ProyectoAdmin)

class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre','apellido_paterno','apellido_materno','numero_celular','fecha_contratacion', 'salario', 'cargo', 'carnet_identidad')
    search_fields = ['apellido_paterno']
admin.site.register(Empleado, EmpleadoAdmin)

class HistorialPagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_modificacion','monto_anterior','monto_actual','motivo_cambio')
    search_fields = ['motivo_cambio']
admin.site.register(HistorialPago, HistorialPagoAdmin)

class EntidadPublicaAdmin(admin.ModelAdmin):
    list_display = ('id', 'representante_legal','contacto','direccion','nombre_entidad')
    search_fields = ['nombre_entidad']
admin.site.register(EntidadPublica, EntidadPublicaAdmin)


class PropuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_presentacion','monto_presupuesto','requisitos','entidad_publica', 'proyecto')
    search_fields = ['requisitos']
admin.site.register(Propuesta, PropuestaAdmin)

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id','nombre','cargo','nit_ci','nombre', 'activo')
    search_fields = ['nombre']
    list_filter = ['activo']

    def get_queryset(self, _request):
        return Cliente.all_objects.all()

admin.site.register(Cliente, ClienteAdmin)

class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'monto','fecha','estado','tipo_pago', 'proyecto')
    search_fields = ['estado']
admin.site.register(Pago, PagoAdmin)
