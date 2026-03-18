from django import forms
from decimal import Decimal, InvalidOperation
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
        fields = ['monto', 'fecha', 'estado', 'tipo_pago', 'proyecto']
        widgets = {
            'fecha':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado':    forms.Select(attrs={'class': 'form-select'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-select'}),
            'proyecto':  forms.Select(attrs={'class': 'form-select'}),
        }

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
        fields = ['monto', 'fecha', 'concepto']
        widgets = {
            'fecha':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'concepto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Anticipo, Saldo final, Mensualidad'}),
        }

    def clean_monto(self):
        valor = str(self.cleaned_data.get('monto', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado
