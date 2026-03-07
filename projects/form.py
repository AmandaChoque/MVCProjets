from django.forms import ModelForm
from django import forms
from .models import Proyecto, Empleado, Pago, EntidadPublica, Cliente, Propuesta

from django.contrib.auth.models import User

# class ProjectForm(ModelForm):
#     class Meta:
#         model =Project
#         fields = ['code', 'name', 'description', 'start_date', 'end_date', 'project_status', 'project_type', 'photo_signed_contract', 'photo_proposed_contract']

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['codigo', 'nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'estado_proyecto', 'tipo_proyecto', 'foto_contrato_firmado', 'monto_total', 'empleado_asignado', 'cliente']
        widgets = {
            'codigo': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'nombre': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el nombre'}),
            'descripcion': forms.Textarea(attrs={'class':'form-control', 'placeholder': 'Escribe la descripcion'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class':'form-control', 'type': 'date'}),
            'estado_proyecto': forms.Select(attrs={'class':'form-select'}),
            'tipo_proyecto': forms.Select(attrs={'class':'form-select'}),
            'foto_contrato_firmado': forms.ClearableFileInput(attrs={'class':'form-control'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto total del proyecto', 'min': '0'}),
            'empleado_asignado': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'})
        }

class EmpleadoForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
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
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'carnet_identidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Carnet de Identidad'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['monto', 'fecha', 'estado', 'tipo_pago', 'proyecto', 'activo']
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto del pago', 'min': '0'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-select'}),
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
            # 'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})  # Para el campo de estado activo
        }

class PublicEntityForm(forms.ModelForm):
    class Meta:
        model = EntidadPublica
        fields = ['representante_legal', 'contacto', 'direccion', 'nombre_entidad']
        widgets = {
            'representante_legal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el representante legal'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el contacto'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección'}),
            'nombre_entidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre de la entidad'}),
        }

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Propuesta
        fields = ['fecha_presentacion', 'monto_presupuesto', 'requisitos', 'entidad_publica']
        widgets = {
            'fecha_presentacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'monto_presupuesto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el monto presupuestado', 'min': '0'}),
            'requisitos': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe los requisitos'}),
            'entidad_publica': forms.Select(attrs={'class': 'form-select'}),

        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['cargo', 'nit_ci', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'direccion', 'tipo_contratante']
        widgets = {
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el cargo'}),
            'nit_ci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el NIT/CI', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '6'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido paterno', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido materno'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el número de teléfono', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección', 'required': 'required'}),
            'tipo_contratante': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
        }

    def clean_nit_ci(self):
        nit = self.cleaned_data.get('nit_ci', '')
        if nit is None:
            return nit
        # Permitir espacios intermedios pero exigir solo dígitos
        nit_digits = nit.replace(' ', '')
        if not nit_digits.isdigit():
            raise forms.ValidationError('El NIT/CI debe contener solo números.')
        if len(nit_digits) < 6:
            raise forms.ValidationError('El NIT/CI debe tener al menos 6 dígitos.')
        return nit_digits

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '')
        if telefono is None:
            return telefono
        telefono_digits = telefono.replace(' ', '')
        if not telefono_digits.isdigit():
            raise forms.ValidationError('El teléfono debe contener solo números.')
        if len(telefono_digits) < 7:
            raise forms.ValidationError('El teléfono debe tener al menos 7 dígitos.')
        return telefono_digits
