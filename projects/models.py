from django.utils import timezone  # Asegúrate de importar timezone desde django.utils

from django.db import models
from django.contrib.auth.models import User

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.db.models import Sum
# Create your models here.

# Auditoria
class AuditModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha Actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Eliminación")
    deleted_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Eliminado por"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

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

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"

    def delete(self, using=None, keep_parents=False):
        """Soft-delete: mark the client inactive instead of removing from DB."""
        self.activo = False
        self.save()


# Empleado
class Empleado(AuditModel):
    # Opciones para el campo "cargo"
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profile")  # Relación uno a uno con User

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

    fecha_contratacion = models.DateField(null=True, blank=True, verbose_name="Fecha Contratación")  # No obligatorio
    salario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Salario")  # No obligatorio
    cargo = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,  # Diccionario de opciones
        default='administrador',  # Valor predeterminado
        verbose_name="Cargo"
    )
    # New CI field
    carnet_identidad = models.CharField(max_length=20, unique=True, verbose_name="Carnet de Identidad")

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
    estado_proyecto = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='pendiente', verbose_name="Estado Proyecto")
    tipo_proyecto = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES, default='instalacion_nueva', verbose_name="Tipo Proyecto")
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de Finalización")
    observacion = models.TextField(blank=True, default='', verbose_name="Observación")
    estado_pago = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', verbose_name="Estado de Pago")
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Creado por")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Contratista")

    monto_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total del Proyecto")

    def __str__(self):
        return self.nombre + ' - by ' + self.creado_por.username

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
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha Modificación")
    monto_anterior = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Anterior")
    monto_actual = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Actual")
    motivo_cambio = models.TextField(verbose_name="Motivo del Cambio")

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='historial_pagos', verbose_name="Proyecto")
    created = models.DateTimeField(default=timezone.now)

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
        )


# Progreso del Proyecto
class Progreso(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='progresos', verbose_name="Proyecto")
    fecha = models.DateField(verbose_name="Fecha")
    porcentaje = models.PositiveIntegerField(verbose_name="Porcentaje (%)")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    observacion = models.TextField(blank=True, verbose_name="Observación")
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Progreso'
        verbose_name_plural = 'Progresos'
        ordering = ['-fecha', '-created']

    def __str__(self):
        return f"{self.proyecto.nombre} — {self.porcentaje}% ({self.fecha})"


# Contrato de Empleado
class ContratoEmpleado(AuditModel):
    empleado = models.ForeignKey(
        Empleado, on_delete=models.CASCADE,
        related_name='contratos', verbose_name="Empleado"
    )
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
        related_name='contratos_empleados', verbose_name="Proyecto"
    )
    fecha_firma = models.DateField(verbose_name="Fecha de Firma")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    monto_acordado = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Acordado (Bs.)")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    documento = models.FileField(upload_to='contratos_empleados/', null=True, blank=True, verbose_name="Documento")

    class Meta:
        verbose_name = 'Contrato de Empleado'
        verbose_name_plural = 'Contratos de Empleados'
        ordering = ['-created']

    def __str__(self):
        return f"Contrato — {self.empleado.nombre} {self.empleado.apellido_paterno} / {self.proyecto.nombre}"


# Contrato del Proyecto (con el cliente)
class ContratoProyecto(AuditModel):
    proyecto = models.OneToOneField(
        Proyecto, on_delete=models.CASCADE,
        related_name='contrato_proyecto', verbose_name="Proyecto"
    )
    fecha_firma = models.DateField(verbose_name="Fecha de Firma")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    monto_acordado = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Acordado (Bs.)")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    documento = models.FileField(upload_to='contratos_proyecto/', null=True, blank=True, verbose_name="Documento")

    class Meta:
        verbose_name = 'Contrato del Proyecto'
        verbose_name_plural = 'Contratos de Proyectos'
        ordering = ['-created']

    def __str__(self):
        return f"Contrato del proyecto — {self.proyecto.nombre}"


