from django.forms import ModelForm
from django import forms
from .models import Project

# class ProjectForm(ModelForm):
#     class Meta:
#         model =Project
#         fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'photo_proposed_contract']

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'photo_proposed_contract']
        widgets = {
            'code': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'description': forms.Textarea(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class':'form-control', 'type': 'date'}),
            'project_status': forms.Select(attrs={'class':'form-control'}),
            'project_type': forms.Select(attrs={'class':'form-control'}),
            'photo_signed_contract': forms.ClearableFileInput(attrs={'class':'form-control'}),
            'photo_proposed_contract': forms.ClearableFileInput(attrs={'class':'form-control'})
        }