from django.contrib import admin

from projects.models import Project, Employee

# Register your models here.
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("created", )
    list_display = ('id', 'name','start_date','end_date','project_status','project_type', 'user')
    search_fields = ['name']
admin.site.register(Project, ProjectAdmin)

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name','last_name_father','last_name_mother','phone_number','hire_date', 'salary', 'position', 'ci')
    search_fields = ['last_name_father']
admin.site.register(Employee, EmployeeAdmin)