from django.utils import timezone  # Asegúrate de importar timezone desde django.utils

from django.db import models
from django.contrib.auth.models import User

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.db.models import Sum
# Create your models here.

# Auditoria
class AuditModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha Actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Eliminación")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        abstract = True


# Contratante
# custom manager to return only active clients by default
class ActiveClienteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Cliente(models.Model):

    TIPO_CONTRATANTE_CHOICES = [
        ('empresa', 'Empresa'),
        ('personal', 'Personal'),
        ('entidad_publica', 'Entidad Pública'),
    ]
    activo = models.BooleanField(default=True, verbose_name="Activo")
    cargo = models.CharField(max_length=50, verbose_name="Cargo")
    nit_ci = models.CharField(max_length=20, verbose_name="NIT/CI")
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, verbose_name="Apellido Materno")
    telefono = models.CharField(max_length=15, verbose_name="Número de Teléfono")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    tipo_contratante = models.CharField(max_length=20, choices=TIPO_CONTRATANTE_CHOICES, default='entidad_publica', verbose_name="Tipo Contratante")
    created = models.DateTimeField(default=timezone.now)

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
class Empleado(models.Model):
    # Opciones para el campo "cargo"
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")  # Relación uno a uno con User
    activo = models.BooleanField(default=True, verbose_name="Activo")

    POSITION_CHOICES = [
        ('gerente_general', 'Gerente General'),
        ('tecnico', 'Técnico'),
        ('analista', 'Analista'),
        ('desarrollador', 'Desarrollador'),
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
        default='gerente_general',  # Valor predeterminado
        verbose_name="Cargo"
    )
    # New CI field
    carnet_identidad = models.CharField(max_length=20, unique=True, verbose_name="Carnet de Identidad")
    created =models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno or ''} - CI: {self.carnet_identidad}"


# EntidadPublica
class EntidadPublica(models.Model):
    activo = models.BooleanField(default=True, verbose_name="Activo")
    representante_legal = models.CharField(max_length=200, verbose_name="Representante Legal")
    contacto = models.CharField(max_length=100, verbose_name="Contacto")
    direccion = models.CharField(max_length=300, verbose_name="Dirección")
    nombre_entidad = models.CharField(max_length=200, verbose_name="Nombre Entidad")
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Entidad Pública'
        verbose_name_plural = 'Entidades Públicas'

    def __str__(self):
        return self.nombre_entidad

# Propuesta
class Propuesta(models.Model):
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_presentacion = models.DateField(verbose_name="Fecha de Presentación")
    monto_presupuesto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Presupuestado")
    requisitos = models.TextField(verbose_name="Requisitos")

    entidad_publica = models.ForeignKey(EntidadPublica, on_delete=models.CASCADE, related_name='propuestas', verbose_name="Entidad Pública")

    created = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Propuesta'
        verbose_name_plural = 'Propuestas'

    def __str__(self):
        return f"Propuesta para {self.entidad_publica}"

# Proyecto
class Proyecto(AuditModel):
    PROJECT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),         # Pendiente
        ('en_progreso', 'En Progreso'), # En Proceso
        ('completado', 'Completado'),     # Terminado
    ]

    PROJECT_TYPE_CHOICES = [
        ('licitacion', 'Licitación'),            # Licitación
        ('contratacion_directa', 'Contratación Directa'),  # Contratación directa
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
    fecha_inicio = models.DateField(verbose_name="Fecha Inicio Proyecto")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha Final Proyecto")
    estado_proyecto = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='pendiente', verbose_name="Estado Proyecto")
    tipo_proyecto = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES, default='contratacion_directa', verbose_name="Tipo Proyecto")
    foto_contrato_firmado = models.ImageField(upload_to="contrato_firmado", null=True, blank=True, verbose_name="Contrato Firmado")
    # photo_proposed_contract = models.ImageField(upload_to="contrato_propueso",null = True, blank= True, verbose_name="Contrato Propuesto")
    estado_pago = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', verbose_name="Estado de Pago")

    # created =models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    empleado_asignado = models.ForeignKey(Empleado, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empleado Asignado")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Contratista")
    propuesta = models.OneToOneField(Propuesta, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Propuesta")

    activo = models.BooleanField(default=True, verbose_name="Activo")

    monto_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total del Proyecto")

    def __str__(self):
        return self.nombre + ' - by ' + self.user.username

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        db_table = 'projects_project'

    def update_payment_status(self):
        """
        Actualiza el estado de pago del proyecto basado en los pagos realizados.
        """
        total_pagado = self.pagos.filter(estado='pagado').aggregate(total_pagado=Sum('monto'))['total_pagado'] or 0

        if total_pagado >= self.monto_total:
            self.estado_pago = 'pagado'
        elif total_pagado > 0:
            self.estado_pago = 'parcial'
        else:
            self.estado_pago = 'no_pagado'

        self.save()

# Pago
class Pago(models.Model):
    # Opciones para el estado del pago
    PAYMENT_STATUS_CHOICES = [
        ('pagado', 'Pagado'),  # Pagado
        ('pendiente', 'Pendiente'),  # Pendiente
    ]

    # Opciones para el tipo de pago
    PAYMENT_TYPE_CHOICES = [
        ('parcial', 'Parcial'),  # Parcial
        ('completo', 'Completo'),  # Completo
    ]

    # Campos del modelo Payment
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    fecha = models.DateField(verbose_name="Fecha Pago")
    estado = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pagado', verbose_name="Estado Pago")
    tipo_pago = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='parcial', verbose_name="Tipo Pago")

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='pagos', verbose_name="Proyecto")
    created = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:

        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f"Pago de {self.monto} - {self.estado}"

    def is_payment_complete(self):
        return self.monto >= self.proyecto.monto_total

    def update_payment_status(self):
        """
        Actualiza el estado del pago y sincroniza el estado de pago del proyecto.
        """
        # Actualizar estado del pago
        if self.monto >= self.proyecto.monto_total:
            self.estado = 'pagado'
        else:
            self.estado = 'pendiente'
        self.save()

        # Actualizar estado de pago del proyecto
        self.proyecto.update_payment_status()

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

@receiver(post_save, sender=Pago)
def update_project_payment_status(sender, instance, **kwargs):
    """
    Actualiza el estado de pago del proyecto cuando se guarda un pago.
    """
    instance.proyecto.update_payment_status()
