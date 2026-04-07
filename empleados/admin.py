from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empleado, ContratoEmpleado, ContratoProyecto, JornadaEmpleado


@admin.register(Empleado)
class EmpleadoAdmin(UserAdmin):
    list_display = ('username', 'nombre', 'apellido_paterno', 'cargo', 'carnet_identidad', 'is_active')
    list_filter = ('is_active', 'cargo', 'is_staff')
    search_fields = ('username', 'nombre', 'apellido_paterno', 'carnet_identidad')
    ordering = ('apellido_paterno', 'nombre')
    list_per_page = 20
    fieldsets = UserAdmin.fieldsets + (
        ('Datos del Empleado', {'fields': ('nombre', 'apellido_paterno', 'apellido_materno', 'cargo', 'carnet_identidad', 'numero_celular')}),
    )


@admin.register(ContratoEmpleado)
class ContratoEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'dias_laborales', 'monto_acordado', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('empleado__nombre', 'empleado__apellido_paterno')
    ordering = ('-created',)


@admin.register(ContratoProyecto)
class ContratoProyectoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'monto_acordado', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('proyecto__nombre',)
    ordering = ('-created',)


@admin.register(JornadaEmpleado)
class JornadaEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'proyecto', 'fecha', 'dias', 'activo')
    list_filter = ('activo', 'dias')
    search_fields = ('contrato__empleado__nombre', 'contrato__empleado__apellido_paterno', 'proyecto__nombre')
    ordering = ('-fecha',)


