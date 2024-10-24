from django.contrib import admin

from projects.models import Project

# Register your models here.
class ProjectAdmin(admin.ModelAdmin):
    readonly_fields = ("created", )
    list_display = ('name','start_date','end_date','project_status','project_type', 'user')
    search_fields = ['name']
admin.site.register(Project, ProjectAdmin)