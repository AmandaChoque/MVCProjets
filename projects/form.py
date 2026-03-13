from django.forms import ModelForm
from django import forms
from django.db.models import Max
from .models import Proyecto, Empleado, Pago, EntidadPublica, Cliente, Propuesta, Progreso, ContratoEmpleado, ContratoProyecto, Proveedor, Insumo, Requiere, Realizar
from django.contrib.auth.models import User
import re
from decimal import Decimal, InvalidOperation


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['codigo', 'nombre', 'descripcion', 'estado_proyecto', 'tipo_proyecto', 'monto_total', 'cliente']
        widgets = {
            'codigo': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el codigo'}),
            'nombre': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Escribe el nombre'}),
            'descripcion': forms.Textarea(attrs={'class':'form-control', 'placeholder': 'Escribe la descripcion'}),
            'estado_proyecto': forms.Select(attrs={'class':'form-select'}),
            'tipo_proyecto': forms.Select(attrs={'class':'form-select'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto total del proyecto', 'min': '0'}),
            'cliente': forms.Select(attrs={'class': 'form-select'})
        }

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

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Ese nombre de usuario ya está en uso.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data


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


class ProgresoForm(forms.ModelForm):
    class Meta:
        model = Progreso
        fields = ['fecha', 'porcentaje', 'descripcion', 'observacion']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'placeholder': 'Ej: 75'}),
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
            # Al editar, excluir el registro actual del cálculo
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            max_porcentaje = qs.aggregate(maximo=Max('porcentaje'))['maximo']
            if max_porcentaje is not None and valor < max_porcentaje:
                raise forms.ValidationError(
                    f'El porcentaje no puede ser menor al máximo ya registrado ({max_porcentaje}%). '
                    f'El progreso no puede retroceder.'
                )
        return valor


class ContratoEmpleadoForm(forms.ModelForm):
    monto_acordado = forms.CharField(
        required=True,
        label="Monto Acordado (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 5000 o 5000.50',
        })
    )

    class Meta:
        model = ContratoEmpleado
        fields = ['empleado', 'fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'observaciones', 'documento']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_firma': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
            'documento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.filter(activo=True)
        self.fields['empleado'].empty_label = None

    def clean_monto_acordado(self):
        valor = self.cleaned_data.get('monto_acordado')
        if not valor:
            raise forms.ValidationError('El monto es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 5000 o 5000.50).')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_documento(self):
        doc = self.cleaned_data.get('documento')
        if doc and hasattr(doc, 'name'):
            name = doc.name.lower()
            allowed_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp')
            if not name.endswith(allowed_extensions):
                raise forms.ValidationError('Solo se permiten archivos PDF o imágenes (JPG, PNG, GIF, WEBP).')
        return doc

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        fecha_firma = cleaned_data.get('fecha_firma')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la fecha de inicio.')
        if fecha_firma and fecha_inicio and fecha_firma > fecha_inicio:
            self.add_error('fecha_firma', 'La fecha de firma no puede ser posterior a la fecha de inicio.')
        return cleaned_data


class ContratoProyectoForm(forms.ModelForm):
    monto_acordado = forms.CharField(
        required=True,
        label="Monto Acordado (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 5000 o 5000.50',
        })
    )

    class Meta:
        model = ContratoProyecto
        fields = ['fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado', 'observaciones', 'documento']
        widgets = {
            'fecha_firma': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales...'}),
            'documento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_monto_acordado(self):
        valor = self.cleaned_data.get('monto_acordado')
        if not valor:
            raise forms.ValidationError('El monto es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 5000 o 5000.50).')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_documento(self):
        doc = self.cleaned_data.get('documento')
        if doc and hasattr(doc, 'name'):
            name = doc.name.lower()
            allowed_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp')
            if not name.endswith(allowed_extensions):
                raise forms.ValidationError('Solo se permiten archivos PDF o imágenes (JPG, PNG, GIF, WEBP).')
        return doc

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        fecha_firma = cleaned_data.get('fecha_firma')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la fecha de inicio.')
        if fecha_firma and fecha_inicio and fecha_firma > fecha_inicio:
            self.add_error('fecha_firma', 'La fecha de firma no puede ser posterior a la fecha de inicio.')
        return cleaned_data


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'rubro', 'celular', 'correo', 'direccion', 'nit']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor', 'required': 'required'}),
            'rubro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rubro o actividad'}),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de celular',
                'inputmode': 'numeric',
                'pattern': '[0-9]+',
                'title': 'Ingrese solo números',
                'required': 'required',
                'minlength': '7',
            }),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NIT del proveedor',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'title': 'Ingrese solo números',
            }),
        }

    def clean_celular(self):
        celular = self.cleaned_data.get('celular', '')
        if not celular:
            return celular
        celular_digits = celular.replace(' ', '')
        if not celular_digits.isdigit():
            raise forms.ValidationError('El celular debe contener solo números.')
        if len(celular_digits) < 7:
            raise forms.ValidationError('El celular debe tener al menos 7 dígitos.')
        return celular_digits

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '')
        if not nit:
            return nit
        nit_digits = nit.replace(' ', '')
        if not nit_digits.isdigit():
            raise forms.ValidationError('El NIT debe contener solo números.')
        return nit_digits


class InsumoForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 150 o 150.50',
        })
    )

    class Meta:
        model = Insumo
        fields = ['nombre', 'marca', 'categoria', 'costo_unitario']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del insumo', 'required': 'required'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_costo_unitario(self):
        valor = self.cleaned_data.get('costo_unitario')
        if not valor:
            raise forms.ValidationError('El costo unitario es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 150 o 150.50). No use comas ni separadores de miles.')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado


class RequerirForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 150 o 150.50',
        })
    )

    class Meta:
        model = Requiere
        fields = ['insumo', 'cantidad', 'costo_unitario']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-select', 'id': 'id_insumo'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insumo'].queryset = Insumo.objects.filter(activo=True)
        self.fields['insumo'].empty_label = 'Seleccionar insumo'

    def clean_costo_unitario(self):
        valor = self.cleaned_data.get('costo_unitario')
        if not valor:
            raise forms.ValidationError('El costo unitario es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 150 o 150.50). No use comas ni separadores de miles.')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado


class RealizarForm(forms.ModelForm):
    costo_unitario = forms.CharField(
        required=True,
        label="Costo Unitario (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 150 o 150.50',
        })
    )

    class Meta:
        model = Realizar
        fields = ['proveedor', 'insumo', 'cantidad', 'costo_unitario', 'fecha']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'insumo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Cantidad'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)
        self.fields['proveedor'].empty_label = 'Seleccionar proveedor'
        self.fields['insumo'].queryset = Insumo.objects.filter(activo=True)
        self.fields['insumo'].empty_label = 'Seleccionar insumo'

    def clean_costo_unitario(self):
        valor = self.cleaned_data.get('costo_unitario')
        if not valor:
            raise forms.ValidationError('El costo unitario es obligatorio.')
        valor_str = str(valor).strip()
        if not re.fullmatch(r'\d+(\.\d{1,2})?', valor_str):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 150 o 150.50). No use comas ni separadores de miles.')
        try:
            resultado = Decimal(valor_str)
        except InvalidOperation:
            raise forms.ValidationError('Ingrese un número válido.')
        if resultado <= 0:
            raise forms.ValidationError('El costo debe ser mayor a cero.')
        return resultado
