from django.forms import ModelForm
from django import forms
from django.db.models import Max
from .models import Proyecto, Empleado, Cliente, Progreso, Contrato
import re
from decimal import Decimal, InvalidOperation

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'


class ProjectForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': 'Debe seleccionar un cliente.'}
    )
    monto_total = forms.CharField(
        required=False,
        label="Monto Estimado (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 5000 o 5000.50 (opcional si se registra contrato)',
        })
    )

    class Meta:
        model = Proyecto
        fields = ['codigo', 'nombre', 'descripcion', 'observacion', 'estado_proyecto', 'tipo_proyecto', 'monto_total', 'cliente']
        widgets = {
            'codigo':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el codigo'}),
            'nombre':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el nombre'}),
            'descripcion':      forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Escribe la descripción'}),
            'observacion':      forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas operativas, observaciones internas...'}),
            'estado_proyecto':  forms.Select(attrs={'class': 'form-select'}),
            'tipo_proyecto':    forms.Select(attrs={'class': 'form-select'}),
            'cliente':          forms.Select(attrs={'class': 'form-select'}),
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

class EmpleadoForm(forms.ModelForm):
    username = forms.CharField(
        label="Usuario (para iniciar sesión)",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: jperez', 'autocomplete': 'off'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=True,
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
            'class': 'form-control',
            'placeholder': 'Número de Celular',
            'inputmode': 'numeric',
            'pattern': '[0-9]+',
            'title': 'Ingrese solo números',
            'required': 'required',
            'minlength': '7',
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
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['cargo', 'nit_ci', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'direccion', 'tipo_contratante', 'nombre_entidad', 'representante_legal']
        widgets = {
            'cargo':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el cargo'}),
            'nit_ci':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el NIT/CI (opcional)', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'title': 'Ingrese solo números'}),
            'nombre':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe los nombres', 'required': 'required'}),
            'apellido_paterno':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido paterno', 'required': 'required'}),
            'apellido_materno':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido materno'}),
            'telefono':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el número de teléfono', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7'}),
            'correo':            forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion':         forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección', 'required': 'required', 'rows': 3}),
            'tipo_contratante':  forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'nombre_entidad':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la institución'}),
            'representante_legal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del representante legal'}),
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


class ProgresoForm(forms.ModelForm):
    class Meta:
        model = Progreso
        fields = ['fecha', 'porcentaje', 'descripcion', 'observacion']
        widgets = {
            'fecha':       forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'porcentaje':  forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'placeholder': 'Ej: 75'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resumen del avance'}),
            'observacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalles adicionales, problemas encontrados, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        self.proyecto = kwargs.pop('proyecto', None)
        super().__init__(*args, **kwargs)

    def clean_porcentaje(self):
        valor = self.cleaned_data.get('porcentaje')
        if valor is None:
            raise forms.ValidationError('El porcentaje es obligatorio.')
        if valor < 0 or valor > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0 y 100.')
        if self.proyecto:
            qs = self.proyecto.progresos.all()
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            max_porcentaje = qs.aggregate(maximo=Max('porcentaje'))['maximo']
            if max_porcentaje is not None and valor < max_porcentaje:
                raise forms.ValidationError(
                    f'El porcentaje no puede ser menor al máximo ya registrado ({max_porcentaje}%). '
                    f'El progreso no puede retroceder.'
                )
        return valor


class _ContratoBaseForm(forms.ModelForm):
    """Campos y validaciones compartidas entre los dos tipos de contrato."""
    monto_acordado = forms.CharField(
        required=True,
        label="Monto Acordado (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5000 o 5000.50'})
    )

    class Meta:
        model = Contrato
        fields = []  # cada subclase define sus fields
        widgets = {
            'empleado':      forms.Select(attrs={'class': 'form-select'}),
            'fecha_firma':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
            'documento':     forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_monto_acordado(self):
        valor = str(self.cleaned_data.get('monto_acordado', '')).strip()
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 5000 o 5000.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_documento(self):
        doc = self.cleaned_data.get('documento')
        if doc and hasattr(doc, 'name'):
            if not doc.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp')):
                raise forms.ValidationError('Solo se permiten archivos PDF o imágenes (JPG, PNG, GIF, WEBP).')
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


class ContratoEmpleadoForm(_ContratoBaseForm):
    class Meta(_ContratoBaseForm.Meta):
        fields = ['empleado', 'fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'tipo_salario', 'observaciones', 'documento']
        widgets = {
            **_ContratoBaseForm.Meta.widgets,
            'tipo_salario': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.filter(is_active=True)
        self.fields['empleado'].empty_label = None


class ContratoProyectoForm(_ContratoBaseForm):
    class Meta(_ContratoBaseForm.Meta):
        fields = ['fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'observaciones', 'documento']
