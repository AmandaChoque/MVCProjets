from django import forms
from decimal import Decimal, InvalidOperation
import re

from .models import Proveedor, Insumo, Requiere, Compra

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class ProveedorForm(forms.ModelForm):
    rubro = forms.ChoiceField(
        choices=[('', 'Seleccionar rubro')] + Proveedor.RUBRO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
        required=True,
        label="Rubro",
    )

    class Meta:
        model = Proveedor
        fields = [
            'nombre', 'rubro', 'nit', 'telefono', 'correo', 'direccion',
            'encargado_nombre', 'encargado_cargo', 'encargado_celular',
        ]
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: DIGIPORT S.R.L.', 'required': 'required'}),
            'nit':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT de la empresa', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'title': 'Ingrese solo números'}),
            'telefono':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de la empresa', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7', 'maxlength': '9'}),
            'correo':    forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@empresa.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección de la empresa'}),
            'encargado_nombre':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo del encargado'}),
            'encargado_cargo':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vendedor, Gerente Comercial'}),
            'encargado_celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Celular del encargado', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'minlength': '7'}),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip().replace(' ', '').replace('-', '')
        if not telefono:
            raise forms.ValidationError('El teléfono es obligatorio.')
        if not telefono.isdigit():
            raise forms.ValidationError('El teléfono debe contener solo números.')
        if len(telefono) < 7:
            raise forms.ValidationError('El teléfono debe tener al menos 7 dígitos.')
        if len(telefono) > 9:
            raise forms.ValidationError('El teléfono no puede superar los 15 dígitos.')
        return telefono

    def clean_encargado_celular(self):
        celular = self.cleaned_data.get('encargado_celular', '').replace(' ', '')
        if celular and not celular.isdigit():
            raise forms.ValidationError('El celular debe contener solo números.')
        if celular and len(celular) < 7:
            raise forms.ValidationError('El celular debe tener al menos 7 dígitos.')
        return celular

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '').replace(' ', '')
        if nit and not nit.isdigit():
            raise forms.ValidationError('El NIT debe contener solo números.')
        return nit


class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'marca', 'modelo', 'categoria', 'unidad_medida', 'stock_minimo']
        widgets = {
            'nombre':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del insumo', 'required': 'required'}),
            'marca':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca'}),
            'modelo':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: IPC-HDW2831T-AS'}),
            'categoria':     forms.Select(attrs={'class': 'form-select'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'stock_minimo':  forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Ej: 5'}),
        }


class RequerirForm(forms.ModelForm):
    class Meta:
        model = Requiere
        fields = ['insumo', 'cantidad']
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


class CompraForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150 o 150.50'})
    )

    class Meta:
        model = Compra
        fields = ['proveedor', 'insumo', 'cantidad', 'costo_unitario', 'fecha', 'numero_factura']
        widgets = {
            'proveedor':      forms.Select(attrs={'class': 'form-select'}),
            'insumo':         forms.Select(attrs={'class': 'form-select'}),
            'cantidad':       forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
            'fecha':          forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'numero_factura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: F-001234 (opcional)'}),
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
