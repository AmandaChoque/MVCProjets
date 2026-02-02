from django.forms import ModelForm
from django import forms
from .models import Project, Empleado, Payment, PublicEntity, Cliente, Proposal

from django.contrib.auth.models import User

# class ProjectForm(ModelForm):
#     class Meta:
#         model =Project
#         fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'photo_proposed_contract']

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'total_amount', 'assigned_employee', 'cliente']
        widgets = {
            'code': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'description': forms.Textarea(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class':'form-control', 'type': 'date'}),
            'project_status': forms.Select(attrs={'class':'form-control'}),
            'project_type': forms.Select(attrs={'class':'form-control'}),
            'photo_signed_contract': forms.ClearableFileInput(attrs={'class':'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto total del proyecto', 'min': '0'}),
            'assigned_employee': forms.Select(attrs={'class': 'form-control', 'style': 'width: 200px;'}),
            'cliente': forms.Select(attrs={'class': 'form-control', 'style': 'width: 200px;'})
        }

class EmpleadoForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Usuario Asociado"
    )
    class Meta:
        model = Empleado
        fields = ['user','nombre', 'apellido_paterno', 'apellido_materno', 'numero_celular', 'fecha_contratacion', 'salario', 'cargo', 'carnet_identidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'numero_celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Teléfono'}),
            'fecha_contratacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Fecha de Contratación'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Salario'}),
            'cargo': forms.Select(attrs={'class': 'form-control'}),
            'carnet_identidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Carnet de Identidad'}),
        }
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date', 'status', 'payment_type', 'project', 'activo']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto del pago', 'min': '0'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),  # Esto permite seleccionar el proyecto desde el formulario
            # 'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})  # Para el campo de estado activo
        }


class PublicEntityForm(forms.ModelForm):
    class Meta:
        model = PublicEntity
        fields = ['legal_representative', 'contact', 'address', 'entity_name']
        widgets = {
            'legal_representative': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el representante legal'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el contacto'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección'}),
            'entity_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre de la entidad'}),
        }

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['submission_date', 'budget_amount', 'requirements', 'public_entity']
        widgets = {
            'submission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'budget_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el monto presupuestado', 'min': '0'}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe los requisitos'}),
            'public_entity': forms.Select(attrs={'class': 'form-control'}),
            
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['position', 'nit_ci', 'first_name', 'paternal_last_name', 'maternal_last_name', 'phone_number', 'address', 'accountant_type']
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el cargo'}),
            'nit_ci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el NIT/CI'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre'}),
            'paternal_last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido paterno'}),
            'maternal_last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido materno'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el número de teléfono'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección'}),
            'accountant_type': forms.Select(attrs={'class': 'form-control'}),
        }