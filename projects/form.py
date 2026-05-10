from django.forms import ModelForm
from django import forms
from .models import Proyecto, Cliente, Sede, FotoSede, TareaChecklist, PagoProyecto, PlantillaTarea, ItemPlantilla, ContratoProyecto, IncidenciaGarantia, AsignacionProyecto
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
            'tipo_proyecto':    forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_proyecto'}),
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

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['tipo_contratante', 'rol_contacto', 'nit_ci', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'direccion', 'nombre_entidad']
        widgets = {
            'rol_contacto':      forms.Select(attrs={'class': 'form-select'}),
            'nit_ci':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el NIT/CI (opcional)', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'title': 'Ingrese solo números'}),
            'nombre':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe los nombres', 'required': 'required'}),
            'apellido_paterno':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido paterno', 'required': 'required'}),
            'apellido_materno':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el apellido materno'}),
            'telefono':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escribe el número de teléfono', 'inputmode': 'numeric', 'pattern': '[0-9]+', 'title': 'Ingrese solo números', 'required': 'required', 'minlength': '7'}),
            'correo':            forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'direccion':         forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la dirección', 'required': 'required', 'rows': 3}),
            'tipo_contratante':  forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'nombre_entidad':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la institución'}),
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



class _ContratoBaseForm(forms.ModelForm):
    """Campos y validaciones compartidas entre los dos tipos de contrato."""
    monto_acordado = forms.CharField(
        required=True,
        label="Monto Acordado (Bs.)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5000 o 5000.50'})
    )

    class Meta:
        model = ContratoProyecto
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


class ContratoProyectoForm(_ContratoBaseForm):
    porcentaje_multa_diaria = forms.CharField(
        required=False,
        label="% Multa Diaria por Retraso",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 2 (deja vacío si no aplica)',
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

    garantia_meses = forms.IntegerField(
        required=False,
        initial=0,
        min_value=0,
        label="Meses de Garantía",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Ej: 12 — 0 si no incluye garantía'}),
    )

    class Meta(_ContratoBaseForm.Meta):
        fields = ['fecha_firma', 'fecha_inicio', 'fecha_fin', 'monto_acordado',
                  'garantia_meses', 'porcentaje_multa_diaria', 'porcentaje_multa_maxima',
                  'observaciones', 'documento']
        widgets = {**_ContratoBaseForm.Meta.widgets}

    def clean_garantia_meses(self):
        valor = self.cleaned_data.get('garantia_meses')
        if valor is None:
            return 0
        if valor < 0:
            raise forms.ValidationError('Los meses de garantía no pueden ser negativos.')
        return valor

    def clean_porcentaje_multa_diaria(self):
        valor = str(self.cleaned_data.get('porcentaje_multa_diaria', '') or '').strip()
        if not valor:
            return Decimal('0')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 2 o 0.50).')
        resultado = Decimal(valor)
        if resultado < 0 or resultado > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0 y 100.')
        return resultado

    def clean_porcentaje_multa_maxima(self):
        valor = str(self.cleaned_data.get('porcentaje_multa_maxima', '') or '').strip()
        if not valor:
            return Decimal('20')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 20).')
        resultado = Decimal(valor)
        if resultado <= 0 or resultado > 100:
            raise forms.ValidationError('El porcentaje debe estar entre 0.01 y 100.')
        return resultado

    def clean(self):
        cleaned_data = super().clean()
        diaria = cleaned_data.get('porcentaje_multa_diaria')
        maxima = cleaned_data.get('porcentaje_multa_maxima')
        if diaria is not None and maxima is not None and diaria > maxima:
            raise forms.ValidationError(
                'El porcentaje de multa diaria no puede superar el tope máximo.'
            )
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
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 400 (dejar en 0 si no aplica)',
            'value': '0',
            'id': 'id_descuento',
        })
    )

    class Meta:
        model = PagoProyecto
        fields = ['monto', 'descuento', 'motivo_descuento', 'fecha', 'tipo_pago', 'numero_referencia', 'proyecto']
        widgets = {
            'fecha':             forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_pago':         forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_pago'}),
            'numero_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: TRX-00123456 (opcional para transferencias)'}),
            'proyecto':          forms.Select(attrs={'class': 'form-select'}),
            'motivo_descuento':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Multa por retraso de 5 días según contrato (Art. 7)'}),
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
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 1500 o 1500.50).')
        resultado = Decimal(valor)
        if resultado <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return resultado

    def clean_descuento(self):
        valor = str(self.cleaned_data.get('descuento', '0') or '0').strip()
        if not valor:
            return Decimal('0')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 400 o 400.50).')
        resultado = Decimal(valor)
        if resultado < 0:
            raise forms.ValidationError('El descuento no puede ser negativo.')
        return resultado


class SedeForm(forms.ModelForm):
    class Meta:
        model = Sede
        fields = ['nombre', 'direccion', 'descripcion', 'latitud', 'longitud', 'plantilla']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Casa #210 Calle 2, Edificio Central', 'required': True}),
            'direccion':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa', 'required': True}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Indicaciones adicionales, referencias, instrucciones de acceso...'}),
            'latitud':     forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ej: -17.3935000', 'id': 'id_latitud'}),
            'longitud':    forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ej: -66.1570000', 'id': 'id_longitud'}),
            'plantilla':   forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plantilla'].queryset = PlantillaTarea.objects.filter(activo=True).order_by('tipo', 'nombre')
        self.fields['plantilla'].required = False
        self.fields['plantilla'].empty_label = 'Seleccionar plantilla'


class PlantillaTareaForm(forms.ModelForm):
    class Meta:
        model = PlantillaTarea
        fields = ['nombre', 'tipo', 'descripcion']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Instalación Cámara IP Exterior'}),
            'tipo':        forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional de esta plantilla...'}),
        }


class ItemPlantillaForm(forms.ModelForm):
    class Meta:
        model = ItemPlantilla
        fields = ['descripcion', 'orden']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Verificar cableado UTP'}),
            'orden':       forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class FotoSedeForm(forms.ModelForm):
    class Meta:
        model = FotoSede
        fields = ['foto', 'descripcion']
        widgets = {
            'foto':        forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Cámara exterior instalada, NVR configurado...'}),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'name'):
            if not foto.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                raise forms.ValidationError('Solo se permiten imágenes (JPG, PNG, GIF, WEBP).')
        return foto


class TareaChecklistForm(forms.ModelForm):
    class Meta:
        model = TareaChecklist
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Tender cable desde tablero, Montar cámara domo exterior...'}),
        }





class IncidenciaGarantiaForm(forms.ModelForm):
    costo_reparacion = forms.CharField(
        required=False,
        label="Costo de reparación (Bs.)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 500 o 500.50 — dejar vacío o 0 si sin costo',
        }),
    )

    class Meta:
        model = IncidenciaGarantia
        fields = ['descripcion', 'fecha_reporte', 'fecha_reparacion', 'costo_reparacion', 'reparado_por', 'estado', 'evidencia']
        widgets = {
            'descripcion':      forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el problema reportado...'}),
            'fecha_reporte':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_reparacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'reparado_por':     forms.Select(attrs={'class': 'form-select'}),
            'estado':           forms.Select(attrs={'class': 'form-select'}),
            'evidencia':        forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from empleados.models import Empleado
        self.fields['reparado_por'].queryset = Empleado.objects.filter(
            is_active=True, cargo__in=('instalador', 'tecnico_soporte')
        ).order_by('apellido_paterno')
        self.fields['reparado_por'].empty_label = 'Sin asignar'

    def clean_costo_reparacion(self):
        valor = str(self.cleaned_data.get('costo_reparacion') or '').strip()
        if not valor:
            return Decimal('0')
        if not re.fullmatch(DECIMAL_REGEX, valor):
            raise forms.ValidationError('Formato inválido. Use punto como separador decimal (ej: 500 o 500.50).')
        resultado = Decimal(valor)
        if resultado < 0:
            raise forms.ValidationError('El costo no puede ser negativo.')
        return resultado

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado')
        fecha_reparacion = cleaned_data.get('fecha_reparacion')
        if estado == 'resuelto' and not fecha_reparacion:
            self.add_error('fecha_reparacion', 'La fecha de reparación es obligatoria cuando el estado es Resuelto.')
        return cleaned_data


class AsignacionProyectoForm(forms.ModelForm):
    class Meta:
        model = AsignacionProyecto
        fields = ['fecha_inicio_plan', 'fecha_fin_plan', 'dias_planificados']
        widgets = {
            'fecha_inicio_plan': forms.DateInput(
                attrs={'class': 'form-control form-control-sm', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'fecha_fin_plan': forms.DateInput(
                attrs={'class': 'form-control form-control-sm', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'dias_planificados': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ej: 12', 'min': 1},
            ),
        }

    def clean(self):
        cd = super().clean()
        fi = cd.get('fecha_inicio_plan')
        ff = cd.get('fecha_fin_plan')
        if fi and ff and ff < fi:
            raise forms.ValidationError('La fecha de fin debe ser posterior a la de inicio.')
        return cd
