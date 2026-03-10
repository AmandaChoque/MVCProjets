from django.forms import ModelForm
from django import forms
from .models import Proyecto, Empleado, Pago, EntidadPublica, Cliente, Propuesta
import re
from decimal import Decimal, InvalidOperation


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
    cargo = forms.ChoiceField(
        choices=[('', 'Seleccionar cargo')] + Empleado.POSITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
        required=True,
        label="Cargo"
    )
    numero_celular = forms.CharField(
        required=True,
        label="Número de Celular",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de Celular',
            'inputmode': 'numeric',
            'pattern': '[0-9]+',
            'title': 'Ingrese solo números',
            'required': 'required',
            'minlength': '7',
        })
    )
    salario = forms.CharField(
        required=False,
        label="Salario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Salario Ej: 1500 o 1500.50',
        })
    )

    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido_paterno', 'apellido_materno', 'numero_celular', 'fecha_contratacion', 'salario', 'cargo', 'carnet_identidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'fecha_contratacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'carnet_identidad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Carnet de Identidad',
                'inputmode': 'numeric',
                'pattern': '[0-9]+',
                'title': 'Ingrese solo números',
                'required': 'required',
                'minlength': '6',
            }),
        }

    def clean_carnet_identidad(self):
        ci = self.cleaned_data.get('carnet_identidad', '')
        if not ci:
            return ci
        ci_digits = ci.replace(' ', '')
        if not ci_digits.isdigit():
            raise forms.ValidationError('El carnet debe contener solo números.')
        if len(ci_digits) < 6:
            raise forms.ValidationError('El carnet debe tener al menos 6 dígitos.')
        return ci_digits

    def clean_salario(self):
        valor = self.cleaned_data.get('salario')
        if valor is None or valor == '':
            return None
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50). No use separadores de miles ni comas.')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado < 0:
            raise forms.ValidationError('El salario no puede ser negativo.')
        return resultado

    def clean_numero_celular(self):
        celular = self.cleaned_data.get('numero_celular', '')
        if not celular:
            return celular
        celular_digits = celular.replace(' ', '')
        if not celular_digits.isdigit():
            raise forms.ValidationError('El celular debe contener solo números.')
        if len(celular_digits) < 7:
            raise forms.ValidationError('El celular debe tener al menos 7 dígitos.')
        return celular_digits

class PaymentForm(forms.ModelForm):
    monto = forms.CharField(
        required=True,
        label="Monto",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1500 o 1500.50',
        })
    )

    class Meta:
        model = Pago
        fields = ['monto', 'fecha', 'estado', 'tipo_pago', 'proyecto']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-select'}),
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_monto(self):
        valor = self.cleaned_data.get('monto')
        if not valor:
            raise forms.ValidationError('El monto es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50). No use comas ni separadores de miles.')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

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
        fields = ['cargo', 'nit_ci', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'direccion', 'tipo_contratante']
        widgets = {
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el cargo'}),
            'nit_ci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el NIT/CI', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '6'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido paterno', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido materno'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el número de teléfono', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección', 'required': 'required', 'rows': 3}),
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
