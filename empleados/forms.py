from django import forms
from django.db.models import Sum
import re
from decimal import Decimal

from .models import Empleado, PagoEmpleado, ContratoEmpleado, JornadaEmpleado
from projects.models import Proyecto

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class EmpleadoForm(forms.ModelForm):
    username = forms.CharField(
        label="Usuario (para iniciar sesión)",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: jperez', 'autocomplete': 'off'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text="Dejar en blanco para mantener la contraseña actual (solo en edición)."
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )
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
            'class': 'form-control', 'placeholder': 'Número de Celular',
            'inputmode': 'numeric', 'pattern': '[0-9]+',
            'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7',
        })
    )
    correo = forms.EmailField(
        required=False,
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'})
    )

    class Meta:
        model = Empleado
        fields = ['nombre', 'apellido_paterno', 'apellido_materno', 'numero_celular', 'cargo', 'carnet_identidad']
        widgets = {
            'nombre':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre', 'required': 'required'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno', 'required': 'required'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno'}),
            'carnet_identidad': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Carnet de Identidad',
                'inputmode': 'numeric', 'pattern': '[0-9]+',
                'title': 'Ingrese solo números', 'required': 'required', 'minlength': '6',
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

    def clean_numero_celular(self):
        celular = self.cleaned_data.get('numero_celular', '').replace(' ', '')
        if not celular.isdigit():
            raise forms.ValidationError('El celular debe contener solo números.')
        if len(celular) < 7:
            raise forms.ValidationError('El celular debe tener al menos 7 dígitos.')
        return celular

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = Empleado.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ese nombre de usuario ya está en uso.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        is_create = not (self.instance and self.instance.pk)
        if is_create and not p1:
            self.add_error('password1', 'La contraseña es obligatoria al crear un empleado.')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data


class _ContratoEmpleadoBase(forms.ModelForm):
    """Campos compartidos entre formularios de contrato de empleado."""
    monto_acordado = forms.CharField(
        required=True,
        label="Monto Acordado (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5000 o 5000.50'})
    )

    class Meta:
        model = ContratoEmpleado
        fields = []
        widgets = {
            'fecha_firma':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'tipo_salario':  forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
            'documento':     forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_monto_acordado(self):
        valor = str(self.cleaned_data.get('monto_acordado', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal.')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_documento(self):
        doc = self.cleaned_data.get('documento')
        if doc and hasattr(doc, 'name'):
            if not doc.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp')):
                raise forms.ValidationError('Solo se permiten archivos PDF o imágenes.')
        return doc

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin    = cleaned_data.get('fecha_fin')
        fecha_firma  = cleaned_data.get('fecha_firma')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la fecha de inicio.')
        if fecha_firma and fecha_inicio and fecha_firma > fecha_inicio:
            self.add_error('fecha_firma', 'La fecha de firma no puede ser posterior a la fecha de inicio.')
        return cleaned_data


class ContratoEmpleadoForm(_ContratoEmpleadoBase):
    class Meta(_ContratoEmpleadoBase.Meta):
        fields = ['empleado', 'fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'tipo_salario', 'observaciones', 'documento']
        widgets = {**_ContratoEmpleadoBase.Meta.widgets, 'empleado': forms.Select(attrs={'class': 'form-select'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.filter(is_active=True)
        self.fields['empleado'].empty_label = None

    def clean(self):
        cleaned_data = super().clean()
        empleado     = cleaned_data.get('empleado')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin    = cleaned_data.get('fecha_fin')
        if empleado:
            qs_activo = ContratoEmpleado.objects.filter(empleado=empleado, activo=True)
            if self.instance and self.instance.pk:
                qs_activo = qs_activo.exclude(pk=self.instance.pk)
            if qs_activo.exists():
                self.add_error('empleado', f'{empleado.nombre} {empleado.apellido_paterno} ya tiene un contrato activo.')
            if fecha_inicio and fecha_fin:
                qs_overlap = ContratoEmpleado.objects.filter(
                    empleado=empleado,
                    fecha_inicio__lte=fecha_fin, fecha_fin__gte=fecha_inicio,
                )
                if self.instance and self.instance.pk:
                    qs_overlap = qs_overlap.exclude(pk=self.instance.pk)
                solapado = qs_overlap.first()
                if solapado:
                    self.add_error('fecha_inicio',
                        f'Las fechas se solapan con un contrato existente ({solapado.fecha_inicio} – {solapado.fecha_fin}).')
        return cleaned_data


class ContratoEmpleadoDesdeEmpleadoForm(_ContratoEmpleadoBase):
    """Contrato de empleado creado desde el perfil del empleado (sin campo empleado)."""
    class Meta(_ContratoEmpleadoBase.Meta):
        fields = ['fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'tipo_salario', 'observaciones', 'documento']

    def __init__(self, *args, empleado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._empleado = empleado

    def clean(self):
        cleaned_data = super().clean()
        if self._empleado:
            qs_activo = ContratoEmpleado.objects.filter(empleado=self._empleado, activo=True)
            if self.instance and self.instance.pk:
                qs_activo = qs_activo.exclude(pk=self.instance.pk)
            if qs_activo.exists():
                raise forms.ValidationError(
                    f'{self._empleado.nombre} {self._empleado.apellido_paterno} ya tiene un contrato activo.')
            fecha_inicio = cleaned_data.get('fecha_inicio')
            fecha_fin    = cleaned_data.get('fecha_fin')
            if fecha_inicio and fecha_fin:
                qs_overlap = ContratoEmpleado.objects.filter(
                    empleado=self._empleado,
                    fecha_inicio__lte=fecha_fin, fecha_fin__gte=fecha_inicio,
                )
                if self.instance and self.instance.pk:
                    qs_overlap = qs_overlap.exclude(pk=self.instance.pk)
                solapado = qs_overlap.first()
                if solapado:
                    self.add_error('fecha_inicio',
                        f'Las fechas se solapan con un contrato existente ({solapado.fecha_inicio} – {solapado.fecha_fin}).')
        return cleaned_data


class JornadaEmpleadoForm(forms.ModelForm):
    dias = forms.ChoiceField(
        choices=JornadaEmpleado.DIAS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Días trabajados',
    )
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Fecha',
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Observación',
    )

    class Meta:
        model = JornadaEmpleado
        fields = ['proyecto', 'fecha', 'dias', 'observacion']
        widgets = {'proyecto': forms.Select(attrs={'class': 'form-select'})}

    def __init__(self, *args, empleado=None, es_admin=False, contrato=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._contrato = contrato
        base_qs = Proyecto.objects.filter(activo=True, estado_proyecto__in=['pendiente', 'en_progreso'])
        if es_admin or empleado is None:
            self.fields['proyecto'].queryset = base_qs
        else:
            self.fields['proyecto'].queryset = base_qs.filter(equipo=empleado)
        self.fields['proyecto'].empty_label = '— Seleccionar proyecto —'

    def clean(self):
        cleaned_data = super().clean()
        fecha    = cleaned_data.get('fecha')
        dias     = cleaned_data.get('dias')
        contrato = self._contrato

        if not fecha or not dias or not contrato:
            return cleaned_data

        dias_decimal = Decimal(str(dias))

        if not (contrato.fecha_inicio <= fecha <= contrato.fecha_fin):
            self.add_error('fecha',
                f'La fecha debe estar entre {contrato.fecha_inicio} y {contrato.fecha_fin} (rango del contrato).')

        qs = JornadaEmpleado.objects.filter(contrato=contrato, fecha=fecha, activo=True)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        dias_ya = qs.aggregate(t=Sum('dias'))['t'] or Decimal('0')
        if dias_ya + dias_decimal > Decimal('1.0'):
            disponible = Decimal('1.0') - dias_ya
            self.add_error('dias',
                f'Ya hay {dias_ya} día(s) registrado(s) en esta fecha. Solo puede agregar {disponible} día(s) más.')

        return cleaned_data


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
