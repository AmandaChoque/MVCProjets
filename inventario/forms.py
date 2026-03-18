from django import forms
from decimal import Decimal, InvalidOperation
import re

from .models import Proveedor, Insumo, Requiere, Realizar

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'rubro', 'celular', 'correo', 'direccion', 'nit']
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor', 'required': 'required'}),
            'rubro':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rubro o actividad'}),
            'celular':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de celular', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7'}),
            'correo':    forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'nit':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT del proveedor', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'title': 'Ingrese solo números'}),
        }

    def clean_celular(self):
        celular = self.cleaned_data.get('celular', '').replace(' ', '')
        if not celular.isdigit():
            raise forms.ValidationError('El celular debe contener solo números.')
        if len(celular) < 7:
            raise forms.ValidationError('El celular debe tener al menos 7 dígitos.')
        return celular

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '').replace(' ', '')
        if nit and not nit.isdigit():
            raise forms.ValidationError('El NIT debe contener solo números.')
        return nit


class InsumoForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150 o 150.50'})
    )

    class Meta:
        model = Insumo
        fields = ['nombre', 'marca', 'categoria', 'costo_unitario', 'stock_minimo']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del insumo', 'required': 'required'}),
            'marca':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca'}),
            'categoria':   forms.Select(attrs={'class': 'form-select'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Ej: 2'}),
        }

    def clean_costo_unitario(self):
        valor = str(self.cleaned_data.get('costo_unitario', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 150 o 150.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado


class RequerirForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150 o 150.50'})
    )

    class Meta:
        model = Requiere
        fields = ['insumo', 'cantidad', 'costo_unitario']
        widgets = {
            'insumo':   forms.Select(attrs={'class': 'form-select', 'id': 'id_insumo'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insumo'].queryset = Insumo.objects.filter(activo=True)
        self.fields['insumo'].empty_label = 'Seleccionar insumo'

    def clean(self):
        cleaned_data = super().clean()
        insumo   = cleaned_data.get('insumo')
        cantidad = cleaned_data.get('cantidad')
        if insumo and cantidad:
            stock_disponible = insumo.stock
            if self.instance and self.instance.pk:
                stock_disponible += self.instance.cantidad
            if cantidad > stock_disponible:
                raise forms.ValidationError(
                    f'Stock insuficiente. Disponible: {stock_disponible} unidad(es) de "{insumo.nombre}".'
                )
        return cleaned_data

    def clean_costo_unitario(self):
        valor = str(self.cleaned_data.get('costo_unitario', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado


class RealizarForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150 o 150.50'})
    )

    class Meta:
        model = Realizar
        fields = ['proveedor', 'insumo', 'cantidad', 'costo_unitario', 'fecha']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'insumo':    forms.Select(attrs={'class': 'form-select'}),
            'cantidad':  forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
            'fecha':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)
        self.fields['proveedor'].empty_label = 'Seleccionar proveedor'
        self.fields['insumo'].queryset = Insumo.objects.filter(activo=True)
        self.fields['insumo'].empty_label = 'Seleccionar insumo'

    def clean_costo_unitario(self):
        valor = str(self.cleaned_data.get('costo_unitario', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado
