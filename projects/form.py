from django.forms import ModelForm
from django import forms
from .models import Project, Employee, Payment

from django.contrib.auth.models import User

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


class EmployeeForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Usuario Asociado"
    )
    class Meta:
        model = Employee
        fields = ['user','first_name', 'last_name_father', 'last_name_mother', 'phone_number', 'hire_date', 'salary', 'position', 'ci']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name_father': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'last_name_mother': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Teléfono'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Fecha de Contratación'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Salario'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'ci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Carnet de Identidad'}),
        }



class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date', 'status', 'payment_type', 'project', 'is_active']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
        }