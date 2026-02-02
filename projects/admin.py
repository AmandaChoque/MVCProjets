from django.contrib import admin

from projects.models import Project, Empleado, PaymentHistory, Payment, Proposal, PublicEntity, Cliente

# Register your models here.
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("created", )
    list_display = ('id', 'name','payment_status','start_date','end_date','project_status','project_type', 'activo','created',
'updated_at',
'deleted_at', 'user')
    search_fields = ['name']
admin.site.register(Project, ProjectAdmin)

class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre','apellido_paterno','apellido_materno','numero_celular','fecha_contratacion', 'salario', 'cargo', 'carnet_identidad')
    search_fields = ['apellido_paterno']
admin.site.register(Empleado, EmpleadoAdmin)

class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'modification_date','previous_amount','current_amount','change_reason')
    search_fields = ['last_name_father']
admin.site.register(PaymentHistory, PaymentHistoryAdmin)

class PublicEntityAdmin(admin.ModelAdmin):
    list_display = ('id', 'legal_representative','contact','address','entity_name')
    search_fields = ['last_name_father']
admin.site.register(PublicEntity, PublicEntityAdmin)


class ProposalAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission_date','budget_amount','requirements','public_entity', 'project')
    search_fields = ['last_name_father']
admin.site.register(Proposal, ProposalAdmin)

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id','position','nit_ci','first_name')
    search_fields = ['last_name_father']
admin.site.register(Cliente, ClienteAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount','date','status','payment_type', 'project')
    search_fields = ['last_name_father']
admin.site.register(Payment, PaymentAdmin)
