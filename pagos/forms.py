from django import forms
from decimal import Decimal
import re

from .models import Pago, PagoEmpleado

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class PaymentForm(forms.ModelForm):
    monto = forms.CharField(
        required=True,
        label="Monto",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1500 o 1500.50'})
    )

    class Meta:
        model = Pago
        fields = ['monto', 'fecha', 'tipo_pago', 'numero_referencia', 'proyecto']
        widgets = {
            'fecha':             forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_pago':         forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_pago'}),
            'numero_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: TRX-00123456 (opcional para transferencias)'}),
            'proyecto':          forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, edit_mode=False, **kwargs):
        super().__init__(*args, **kwargs)
        from projects.models import Proyecto
        self.fields['proyecto'].queryset = Proyecto.objects.filter(activo=True)
        if edit_mode:
            self.fields.pop('monto')
            self.fields.pop('proyecto')

    def clean_monto(self):
        valor = str(self.cleaned_data.get('monto', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado


class PagoEmpleadoForm(forms.ModelForm):
    monto = forms.CharField(
        required=True,
        label="Monto (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1500 o 1500.50'})
    )

    class Meta:
        model = PagoEmpleado
        fields = ['monto', 'fecha', 'concepto', 'tipo_pago']
        widgets = {
            'fecha':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'concepto':  forms.Select(attrs={'class': 'form-select'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_monto(self):
        valor = str(self.cleaned_data.get('monto', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado
