from django.forms import ModelForm
from .models import Project

class ProjectForm(ModelForm):
    class Meta:
        model =Project
        fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'photo_proposed_contract']