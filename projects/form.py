from django import forms
from .models import Proyecto, Cliente, Sede, TareaChecklist, PagoProyecto
import re
from decimal import Decimal, InvalidOperation

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class ProjectForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=True,
        empty_label='Seleccionar cliente',
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Debe seleccionar un cliente.'}
    )
    monto_total = forms.CharField(
        required=False,
        label="Monto Total del Proyecto (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 5000 o 5000.50',
        })
    )
    monto_acordado = forms.CharField(
        required=False,
        label="Monto Acordado en Contrato (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 5000 o 5000.50 (opcional)',
        })
    )
    porcentaje_multa_diaria = forms.CharField(
        required=False,
        label="% Multa Diaria por Retraso",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 2 (dejar vacío si no aplica)',
        }),
    )
    porcentaje_multa_maxima = forms.CharField(
        required=False,
        label="% Multa Máxima (tope)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 20',
        }),
    )

    class Meta:
        model = Proyecto
        fields = [
            'codigo', 'nombre', 'descripcion', 'objetivo_general', 'descripcion_alcance',
            'acta_inicio', 'observacion', 'estado_proyecto', 'tipo_proyecto',
            'monto_total', 'cliente',
            'fecha_fin_contrato', 'monto_acordado', 'porcentaje_multa_diaria',
            'porcentaje_multa_maxima', 'garantia_meses', 'documento_contrato',
            'nivel_riesgo', 'descripcion_riesgo',
        ]
        widgets = {
            'codigo':               forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PROY-001'}),
            'nombre':               forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proyecto'}),
            'descripcion':          forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objetivo_general':     forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion_alcance':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'acta_inicio':          forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'observacion':          forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado_proyecto':      forms.Select(attrs={'class': 'form-select'}),
            'tipo_proyecto':        forms.Select(attrs={'class': 'form-select'}),
            'fecha_fin_contrato':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'garantia_meses':       forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Ej: 12 — 0 si no incluye garantía'}),
            'documento_contrato':   forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nivel_riesgo':         forms.Select(attrs={'class': 'form-select'}),
            'descripcion_riesgo':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ej: Acceso limitado a la ubicación. Plan: coordinar con cliente con 2 días de anticipación.'}),
        }

    def clean_monto_total(self):
        valor = self.cleaned_data.get('monto_total')
        if not valor or str(valor).strip() == '':
            return 0
        valor_str = str(valor).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 5000 o 5000.50).')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado < 0:
            raise forms.ValidationError('El monto no puede ser negativo.')
        return resultado

    def clean_monto_acordado(self):
        valor = str(self.cleaned_data.get('monto_acordado', '') or '').strip()
        if not valor:
            return None
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_porcentaje_multa_diaria(self):
        valor = str(self.cleaned_data.get('porcentaje_multa_diaria', '') or '').strip()
        if not valor:
            return Decimal('0')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado < 0 or resultado > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0 y 100.')
        return resultado

    def clean_porcentaje_multa_maxima(self):
        valor = str(self.cleaned_data.get('porcentaje_multa_maxima', '') or '').strip()
        if not valor:
            return Decimal('20')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0 or resultado > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0.01 y 100.')
        return resultado


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['rol_contacto', 'nit_ci', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'direccion', 'tipo_contratante', 'nombre_entidad']
        widgets = {
            'rol_contacto':     forms.Select(attrs={'class': 'form-select'}),
            'nit_ci':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT/CI (opcional)', 'inputmode': 'numeric'}),
            'nombre':           forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono':         forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'required': 'required', 'minlength': '7'}),
            'correo':           forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion':        forms.Textarea(attrs={'class': 'form-control', 'required': 'required', 'rows': 3}),
            'tipo_contratante': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'nombre_entidad':   forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_nit_ci(self):
        nit = self.cleaned_data.get('nit_ci', '').strip()
        if not nit:
            return ''
        nit_digits = nit.replace(' ', '')
        if not nit_digits.isdigit():
            raise forms.ValidationError('El NIT/CI debe contener solo números.')
        if len(nit_digits) < 6:
            raise forms.ValidationError('El NIT/CI debe tener al menos 6 dígitos.')
        return nit_digits

    def clean_nombre(self):
        return self.cleaned_data.get('nombre', '').strip().title()

    def clean_apellido_paterno(self):
        return self.cleaned_data.get('apellido_paterno', '').strip().title()

    def clean_apellido_materno(self):
        return self.cleaned_data.get('apellido_materno', '').strip().title()

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').replace(' ', '')
        if not telefono.isdigit():
            raise forms.ValidationError('El teléfono debe contener solo números.')
        if len(telefono) < 7:
            raise forms.ValidationError('El teléfono debe tener al menos 7 dígitos.')
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_contratante')
        if tipo == 'entidad_publica':
            if not cleaned_data.get('nombre_entidad', '').strip():
                self.add_error('nombre_entidad', 'Este campo es obligatorio para Entidad Pública.')
        return cleaned_data


class PaymentForm(forms.ModelForm):
    monto = forms.CharField(
        required=True,
        label="Monto recibido (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1500 o 1500.50'})
    )
    descuento = forms.CharField(
        required=False,
        label="Descuento / Multa aplicada (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 400 (0 si no aplica)', 'value': '0', 'id': 'id_descuento'})
    )

    class Meta:
        model = PagoProyecto
        fields = ['monto', 'descuento', 'motivo_descuento', 'fecha', 'tipo_pago', 'numero_referencia', 'proyecto']
        widgets = {
            'fecha':             forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_pago':         forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_pago'}),
            'numero_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: TRX-00123456 (opcional)'}),
            'proyecto':          forms.Select(attrs={'class': 'form-select'}),
            'motivo_descuento':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Multa por retraso'}),
        }

    def __init__(self, *args, edit_mode=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.filter(activo=True).exclude(
            estado_proyecto='completado', estado_pago='pagado'
        )
        self.fields['motivo_descuento'].required = False
        if edit_mode:
            self.fields.pop('monto')
            self.fields.pop('descuento')
            self.fields.pop('motivo_descuento')
            self.fields.pop('proyecto')

    def clean_monto(self):
        valor = str(self.cleaned_data.get('monto', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_descuento(self):
        valor = str(self.cleaned_data.get('descuento', '0') or '0').strip()
        if not valor:
            return Decimal('0')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado < 0:
            raise forms.ValidationError('El descuento no puede ser negativo.')
        return resultado


class SedeForm(forms.ModelForm):
    class Meta:
        model = Sede
        fields = ['nombre', 'direccion', 'descripcion', 'latitud', 'longitud']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'direccion':   forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'latitud':     forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ej: -17.3935000', 'id': 'id_latitud'}),
            'longitud':    forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ej: -66.1570000', 'id': 'id_longitud'}),
        }


class TareaChecklistForm(forms.ModelForm):
    class Meta:
        model = TareaChecklist
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Tender cable desde tablero...'}),
        }
