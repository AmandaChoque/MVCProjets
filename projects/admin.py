from django.contrib import admin

from projects.models import Project, Employee, PaymentHistory, Payment, Proposal, PublicEntity, Contractor

# Register your models here.
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("created", )
    list_display = ('id', 'name','start_date','end_date','project_status','project_type', 'is_active','created',
'updated_at',
'deleted_at', 'user')
    search_fields = ['name']
admin.site.register(Project, ProjectAdmin)

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name','last_name_father','last_name_mother','phone_number','hire_date', 'salary', 'position', 'ci')
    search_fields = ['last_name_father']
admin.site.register(Employee, EmployeeAdmin)

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

class ContractorAdmin(admin.ModelAdmin):
    list_display = ('id', 'entity_place_representation','position','nit_ci','first_name')
    search_fields = ['last_name_father']
admin.site.register(Contractor, ContractorAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount','date','status','payment_type', 'project')
    search_fields = ['last_name_father']
admin.site.register(Payment, PaymentAdmin)

