from django.utils import timezone
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.db.models import Sum
from django.core.validators import MaxValueValidator
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
    estado_pago = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', db_index=True, verbose_name="Estado de Pago")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Contratista")

    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto Total del Proyecto")

    def __str__(self):
        username = self.creado_por.username if self.creado_por else 'N/A'
        return self.nombre + ' - by ' + username

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        db_table = 'projects_project'

    def update_payment_status(self):
        """
        Actualiza el estado de pago del proyecto basado en los pagos realizados.
        """
        total_pagado = self.pagos.filter(estado='pagado', activo=True).aggregate(total_pagado=Sum('monto'))['total_pagado'] or 0

        if total_pagado >= self.monto_total:
            self.estado_pago = 'pagado'
        elif total_pagado > 0:
            self.estado_pago = 'parcial'
        else:
            self.estado_pago = 'no_pagado'

        self.save()

# HistorialPagos
class HistorialPago(models.Model):
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
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='historial_pagos', verbose_name="Proyecto")

    class Meta:
        verbose_name = 'Historial Pago'
        verbose_name_plural = 'Historiales de Pagos'

    def __str__(self):
        return f"Historial de Pago - Modificado en {self.fecha_modificacion}"

@receiver(pre_save, sender=Proyecto)
def registrar_cambio_monto_proyecto(sender, instance, **kwargs):
    """
    Registra en HistorialPago cuando cambia el monto_total de un proyecto.
    """
    if not instance.pk:
        return  # proyecto nuevo, no hay historial que registrar
    try:
        anterior = Proyecto.objects.get(pk=instance.pk)
    except Proyecto.DoesNotExist:
        return
    if anterior.monto_total != instance.monto_total:
        HistorialPago.objects.create(
            proyecto=anterior,
            monto_anterior=anterior.monto_total,
            monto_actual=instance.monto_total,
            motivo_cambio=f'Monto actualizado de Bs. {anterior.monto_total} a Bs. {instance.monto_total}.',
            modificado_por=getattr(instance, '_current_user', None),
        )


# Progreso del Proyecto
class Progreso(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='progresos', verbose_name="Proyecto")
    fecha = models.DateField(verbose_name="Fecha")
    porcentaje = models.PositiveIntegerField(validators=[MaxValueValidator(100)], verbose_name="Porcentaje (%)")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    observacion = models.TextField(blank=True, verbose_name="Observación")
    created = models.DateTimeField(default=timezone.now)

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
        ('mensual', 'Mensual'),
        ('diario',  'Diario'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo de Contrato")
    tipo_salario = models.CharField(max_length=10, choices=TIPO_SALARIO_CHOICES, default='mensual', null=True, blank=True, verbose_name="Tipo de Pago")
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
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
            )
        ]

    def __str__(self):
        if self.tipo == 'empleado' and self.empleado:
            return f"Contrato empleado — {self.empleado.nombre} {self.empleado.apellido_paterno} / {self.proyecto.nombre}"
        return f"Contrato proyecto — {self.proyecto.nombre}"


# Alias para compatibilidad con imports existentes
ContratoEmpleado = Contrato
ContratoProyecto = Contrato


