from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from django.db.models import Sum
from django.core.validators import MaxValueValidator, MinValueValidator
# Create your models here.

# Auditoria
class AuditModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha Actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Eliminación")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Eliminado por"
    )
    activo = models.BooleanField(default=True, db_index=True, verbose_name="Activo")

    class Meta:
        abstract = True


# Contratante
# custom manager to return only active clients by default
class ActiveClienteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Cliente(AuditModel):

    TIPO_CONTRATANTE_CHOICES = [
        ('empresa', 'Empresa'),
        ('personal', 'Personal'),
        ('entidad_publica', 'Entidad Pública'),
    ]
    cargo = models.CharField(max_length=50, verbose_name="Cargo")
    nit_ci = models.CharField(max_length=20, blank=True, default='', verbose_name="NIT/CI")
    nombre = models.CharField(max_length=50, verbose_name="Nombres")
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, blank=True, default='', verbose_name="Apellido Materno")
    telefono = models.CharField(max_length=15, verbose_name="Número de Teléfono")
    correo = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Correo Electrónico")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    tipo_contratante = models.CharField(max_length=20, choices=TIPO_CONTRATANTE_CHOICES, default='entidad_publica', verbose_name="Tipo Contratante")
    # Solo para tipo_contratante = 'entidad_publica'
    nombre_entidad = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de la Entidad")
    representante_legal = models.CharField(max_length=200, blank=True, null=True, verbose_name="Representante Legal")

    # managers
    objects = ActiveClienteManager()           # default manager filters activo=True
    all_objects = models.Manager()             # explicit manager returning all rows

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        constraints = [
            models.UniqueConstraint(
                fields=['nit_ci'],
                condition=~Q(nit_ci=''),
                name='unique_nit_ci_when_not_empty',
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"

    def delete(self, using=None, keep_parents=False):
        """Soft-delete: mark the client inactive instead of removing from DB."""
        self.activo = False
        self.save()


# Empleado (es también el usuario del sistema)
class Empleado(AbstractUser):
    POSITION_CHOICES = [
        ('administrador', 'Administrador'),
        ('gerente', 'Gerente'),
        ('instalador', 'Instalador'),
        ('tecnico_soporte', 'Técnico de Soporte'),
        ('secretaria', 'Secretaria'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido_paterno = models.CharField(max_length=100, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apellido Materno")
    numero_celular = models.CharField(max_length=15, blank=True, verbose_name="Numero Celular")
    cargo = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        default='administrador',
        verbose_name="Cargo"
    )
    carnet_identidad = models.CharField(max_length=20, unique=True, verbose_name="Carnet de Identidad")
    # is_active ya existe en AbstractUser — no se repite aquí

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno or ''} - CI: {self.carnet_identidad}"



# Proyecto
class Proyecto(AuditModel):
    PROJECT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),         # Pendiente
        ('en_progreso', 'En Progreso'), # En Proceso
        ('completado', 'Completado'),     # Terminado
    ]

    PROJECT_TYPE_CHOICES = [
        ('instalacion_nueva', 'Instalación Nueva'),
        ('ampliacion', 'Ampliación'),
        ('mantenimiento', 'Mantenimiento'),
        ('emergencia', 'Emergencia'),
    ]
    # Opciones para el estado del pago
    PAYMENT_STATE_CHOICES = [
        ('no_pagado', 'No Pagado'),
        ('parcial', 'Pago Parcial'),
        ('pagado', 'Pagado Completo'),
    ]
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código Proyecto")
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre Proyecto")
    descripcion = models.TextField(blank=True, verbose_name="Descripción Proyecto")
    estado_proyecto = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='pendiente', db_index=True, verbose_name="Estado Proyecto")
    tipo_proyecto = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES, default='instalacion_nueva', db_index=True, verbose_name="Tipo Proyecto")
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Finalización")
    observacion = models.TextField(blank=True, default='', verbose_name="Observación")
    # Desnormalización controlada: valor calculado mantenido automáticamente
    # por la señal post_save/post_delete de Pago. Nunca modificar directamente.
    estado_pago = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', db_index=True, verbose_name="Estado de Pago")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    # null=True por compatibilidad de datos. El formulario lo exige siempre (blank=False en ProjectForm).
    # Todo proyecto debe tener cliente asignado — esta restricción se refuerza en capa de formulario.
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Contratista")

    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Monto Total del Proyecto")

    def __str__(self):
        username = self.creado_por.username if self.creado_por else 'N/A'
        return self.nombre + ' - by ' + username

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        db_table = 'projects_project'
        constraints = [
            # Ambas fechas son opcionales; la restricción solo aplica cuando ambas están presentes
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_inicio__isnull=True) | Q(fecha_fin__gte=models.F('fecha_inicio')),
                name='proyecto_fecha_fin_gte_inicio',
            ),
        ]

    def _sync_estado_pago(self):
        """
        Recalcula y persiste el campo estado_pago.
        Uso exclusivo de señales — no llamar desde vistas ni formularios.
        """
        total_pagado = self.pagos.filter(activo=True).aggregate(total_pagado=Sum('monto'))['total_pagado'] or 0

        if total_pagado >= self.monto_total:
            self.estado_pago = 'pagado'
        elif total_pagado > 0:
            self.estado_pago = 'parcial'
        else:
            self.estado_pago = 'no_pagado'

        self.save()

# Auditoría de cambios al presupuesto del proyecto
class HistorialPresupuesto(models.Model):
    fecha_modificacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Modificación")
    monto_anterior = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Anterior")
    monto_actual = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Actual")
    motivo_cambio = models.TextField(verbose_name="Motivo del Cambio")
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Modificado por"
    )
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='historial_presupuesto', verbose_name="Proyecto")

    class Meta:
        verbose_name = 'Historial Presupuesto'
        verbose_name_plural = 'Historiales de Presupuesto'
        db_table = 'projects_historialpresupuesto'

    def __str__(self):
        return f"Presupuesto modificado — {self.fecha_modificacion}"

@receiver(pre_save, sender=Proyecto)
def registrar_cambio_monto_proyecto(sender, instance, **kwargs):
    """
    Registra en HistorialPresupuesto cuando cambia el monto_total.
    Además marca el proyecto para que post_save recalcule estado_pago,
    cerrando el ciclo: cambio de presupuesto → estado de cobro actualizado.
    """
    if not instance.pk:
        return
    try:
        anterior = Proyecto.objects.get(pk=instance.pk)
    except Proyecto.DoesNotExist:
        return
    if anterior.monto_total != instance.monto_total:
        HistorialPresupuesto.objects.create(
            proyecto=anterior,
            monto_anterior=anterior.monto_total,
            monto_actual=instance.monto_total,
            motivo_cambio=f'Monto actualizado de Bs. {anterior.monto_total} a Bs. {instance.monto_total}.',
            modificado_por=getattr(instance, '_current_user', None),
        )
        instance._recalcular_estado_pago = True  # bandera para post_save


@receiver(post_save, sender=Proyecto)
def sync_estado_pago_tras_cambio_monto(sender, instance, **kwargs):
    """
    Si el monto_total cambió, recalcula estado_pago para mantener consistencia.
    Evita recursión usando update_fields para no disparar pre_save de nuevo.
    """
    if getattr(instance, '_recalcular_estado_pago', False):
        instance._recalcular_estado_pago = False
        total_pagado = instance.pagos.filter(activo=True).aggregate(
            t=Sum('monto'))['t'] or 0
        if total_pagado >= instance.monto_total:
            nuevo_estado = 'pagado'
        elif total_pagado > 0:
            nuevo_estado = 'parcial'
        else:
            nuevo_estado = 'no_pagado'
        if instance.estado_pago != nuevo_estado:
            Proyecto.objects.filter(pk=instance.pk).update(estado_pago=nuevo_estado)


# Progreso del Proyecto
class Progreso(AuditModel):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='progresos', verbose_name="Proyecto")
    fecha = models.DateField(verbose_name="Fecha")
    porcentaje = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Porcentaje (%)")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    observacion = models.TextField(blank=True, verbose_name="Observación")

    class Meta:
        verbose_name = 'Progreso'
        verbose_name_plural = 'Progresos'
        ordering = ['-fecha', '-created']

    def __str__(self):
        return f"{self.proyecto.nombre} — {self.porcentaje}% ({self.fecha})"


# Contrato unificado (con empleado o con cliente/proyecto)
class Contrato(AuditModel):
    TIPO_CHOICES = [
        ('empleado', 'Contrato con Empleado'),
        ('proyecto', 'Contrato con Cliente'),
    ]
    TIPO_SALARIO_CHOICES = [
        ('mensual', 'Mensual (30 días)'),
        ('semanal', 'Semanal (7 días)'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo de Contrato")
    tipo_salario = models.CharField(max_length=10, choices=TIPO_SALARIO_CHOICES, default='mensual', null=True, blank=True, verbose_name="Tipo de Pago")
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='contratos', verbose_name="Proyecto"
    )
    # Solo para tipo='empleado'
    empleado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='contratos', verbose_name="Empleado"
    )
    fecha_firma = models.DateField(verbose_name="Fecha de Firma")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    monto_acordado = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Acordado (Bs.)")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    documento = models.FileField(upload_to='contratos/', null=True, blank=True, verbose_name="Documento")

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-created']
        constraints = [
            models.CheckConstraint(
                condition=~Q(tipo='empleado') | Q(empleado__isnull=False),
                name='contrato_empleado_required_when_tipo_empleado',
            ),
            models.CheckConstraint(
                condition=~Q(tipo='proyecto') | Q(proyecto__isnull=False),
                name='contrato_proyecto_required_when_tipo_proyecto',
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__gte=models.F('fecha_inicio')),
                name='contrato_fecha_fin_gte_inicio',
            ),
            models.CheckConstraint(
                condition=Q(fecha_firma__lte=models.F('fecha_inicio')),
                name='contrato_fecha_firma_lte_inicio',
            ),
            # Un proyecto solo puede tener un contrato con el cliente activo a la vez
            models.UniqueConstraint(
                fields=['proyecto'],
                condition=Q(tipo='proyecto', activo=True),
                name='unique_contrato_proyecto_activo',
            ),
        ]

    def __str__(self):
        if self.tipo == 'empleado' and self.empleado:
            proyecto_str = f" / {self.proyecto.nombre}" if self.proyecto else ""
            return f"Contrato empleado — {self.empleado.nombre} {self.empleado.apellido_paterno}{proyecto_str}"
        return f"Contrato proyecto — {self.proyecto.nombre}"

    @property
    def monto_diario(self):
        """Monto a pagar por cada día trabajado según el período del contrato."""
        if self.tipo == 'empleado' and self.monto_acordado:
            divisor = 7 if self.tipo_salario == 'semanal' else 30
            return self.monto_acordado / divisor
        return self.monto_acordado


class JornadaEmpleado(AuditModel):
    """Registro diario de trabajo de un empleado: en qué proyecto trabajó y cuánto."""
    DIAS_CHOICES = [
        ('0.5', 'Medio día (0.5)'),
        ('1.0', 'Día completo (1.0)'),
    ]

    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE,
        related_name='jornadas', verbose_name="Contrato"
    )
    proyecto = models.ForeignKey(
        'Proyecto', on_delete=models.PROTECT,
        related_name='jornadas_empleados', verbose_name="Proyecto trabajado"
    )
    fecha = models.DateField(verbose_name="Fecha")
    dias = models.DecimalField(
        max_digits=3, decimal_places=1, default=1.0,
        verbose_name="Días trabajados",
        validators=[MinValueValidator(0.5), MaxValueValidator(1.0)],
    )
    observacion = models.TextField(blank=True, verbose_name="Observación")

    class Meta:
        verbose_name = 'Jornada de Empleado'
        verbose_name_plural = 'Jornadas de Empleados'
        ordering = ['-fecha']

    def __str__(self):
        emp = self.contrato.empleado
        return f"{emp.nombre} {emp.apellido_paterno} — {self.fecha} ({self.dias}d) — {self.proyecto.nombre}"

    @property
    def monto(self):
        """Monto a cobrar por esta jornada."""
        return self.dias * self.contrato.monto_diario


