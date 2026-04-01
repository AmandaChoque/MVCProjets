from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import pre_save, post_save, post_delete
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
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, verbose_name="Contratista")

    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Monto Total del Proyecto")
    equipo = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='proyectos_asignados',
        verbose_name="Equipo del Proyecto",
    )

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
            models.CheckConstraint(
                condition=Q(monto_total__gte=0),
                name='proyecto_monto_total_no_negativo',
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


# ── Sede (punto de instalación dentro de un proyecto) ────────────────────────

class Sede(AuditModel):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado',  'Completado'),
    ]

    proyecto    = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='sedes', verbose_name="Proyecto")
    nombre      = models.CharField(max_length=200, verbose_name="Nombre / Referencia")
    direccion   = models.CharField(max_length=500, verbose_name="Dirección")
    descripcion = models.TextField(blank=True, verbose_name="Descripción / Indicaciones")
    latitud     = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Latitud")
    longitud    = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Longitud")
    estado      = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")

    class Meta:
        verbose_name = 'Sede de Instalación'
        verbose_name_plural = 'Sedes de Instalación'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} — {self.proyecto.nombre}"

    @property
    def porcentaje_checklist(self):
        """Porcentaje de tareas completadas (0-100)."""
        total = self.tareas.filter(activo=True).count()
        if total == 0:
            return 0
        completadas = self.tareas.filter(activo=True, completado=True).count()
        return round(completadas / total * 100)

    def _sync_estado(self):
        """Actualiza estado según tareas completadas. Llamar tras cada cambio de tarea."""
        pct = self.porcentaje_checklist
        if pct == 100:
            nuevo = 'completado'
        elif pct > 0:
            nuevo = 'en_progreso'
        else:
            nuevo = 'pendiente'
        if self.estado != nuevo:
            self.estado = nuevo
            self.save(update_fields=['estado'])


# ── Foto de sede ──────────────────────────────────────────────────────────────

class FotoSede(AuditModel):
    sede        = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='fotos', verbose_name="Sede")
    foto        = models.ImageField(upload_to='sedes/fotos/', verbose_name="Foto")
    descripcion = models.CharField(max_length=255, blank=True, verbose_name="Descripción")
    subida_por  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name="Subida por"
    )

    class Meta:
        verbose_name = 'Foto de Sede'
        verbose_name_plural = 'Fotos de Sede'
        ordering = ['-created']

    def __str__(self):
        return f"Foto — {self.sede.nombre} ({self.created.date() if self.created else ''})"


# ── Tarea de checklist por sede ───────────────────────────────────────────────

class TareaChecklist(AuditModel):
    sede              = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='tareas', verbose_name="Sede")
    descripcion       = models.CharField(max_length=255, verbose_name="Tarea")
    orden             = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")
    completado        = models.BooleanField(default=False, verbose_name="Completado")
    fecha_completado  = models.DateTimeField(null=True, blank=True, verbose_name="Fecha completado")
    completado_por    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="Completado por"
    )

    class Meta:
        verbose_name = 'Tarea Checklist'
        verbose_name_plural = 'Tareas Checklist'
        ordering = ['orden', 'created']
        constraints = [
            models.CheckConstraint(
                condition=~Q(completado=True) | Q(completado_por__isnull=False),
                name='tarea_completado_por_requerido_si_completado',
            ),
        ]

    def __str__(self):
        estado = '✓' if self.completado else '○'
        return f"{estado} {self.descripcion} — {self.sede.nombre}"


# ── Notificación interna ──────────────────────────────────────────────────────

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('sede_completada',  'Sede completada'),
        ('tarea_completada', 'Tarea completada'),
        ('general',         'General'),
    ]

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notificaciones', verbose_name="Destinatario"
    )
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, default='general', verbose_name="Tipo")
    mensaje     = models.TextField(verbose_name="Mensaje")
    leida       = models.BooleanField(default=False, db_index=True, verbose_name="Leída")
    proyecto    = models.ForeignKey(Proyecto, on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name="Proyecto")
    sede        = models.ForeignKey('Sede', on_delete=models.CASCADE, null=True, blank=True, related_name='+', verbose_name="Sede")
    fecha       = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha']
        constraints = [
            models.CheckConstraint(
                condition=~Q(tipo='sede_completada') | Q(sede__isnull=False),
                name='notificacion_sede_requerida_si_tipo_sede',
            ),
        ]

    def __str__(self):
        return f"[{self.tipo}] → {self.destinatario.username}: {self.mensaje[:60]}"


# ── Señal: al completar todas las tareas de una sede, notificar a admins/gerentes ──

# ── Pago del cliente al proyecto ─────────────────────────────────────────────

METODOS_PAGO = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
]


class Pago(AuditModel):
    monto             = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs.)")
    fecha             = models.DateField(db_index=True, verbose_name="Fecha de Pago")
    tipo_pago         = models.CharField(max_length=15, choices=METODOS_PAGO, default='efectivo', verbose_name="Método de Pago")
    numero_referencia = models.CharField(max_length=100, blank=True, default='', verbose_name="N° Referencia / Comprobante")
    proyecto          = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='pagos', verbose_name="Proyecto")

    class Meta:
        verbose_name_plural = 'Pagos'
        db_table = 'projects_pago'
        ordering = ['-fecha']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='pago_monto_positivo',
            )
        ]

    def __str__(self):
        return f"Pago de {self.monto} ({self.get_tipo_pago_display()})"


@receiver(post_save, sender='projects.Pago')
@receiver(post_delete, sender='projects.Pago')
def update_project_payment_status(sender, instance, **kwargs):
    instance.proyecto._sync_estado_pago()


# ── Señal: notificaciones de sede ────────────────────────────────────────────

@receiver(post_save, sender=TareaChecklist)
def notificar_sede_completada(sender, instance, **kwargs):
    """
    Cuando una tarea se marca como completada, sincroniza el estado de la sede.
    Si la sede llega a 100%, crea notificaciones para todos los admins/gerentes.
    """
    if not instance.activo:
        return
    sede = instance.sede
    sede._sync_estado()
    sede.refresh_from_db(fields=['estado'])

    # ── Sincronizar estado_proyecto según progreso de sedes ───────────────────
    proyecto = sede.proyecto
    sedes_activas = list(proyecto.sedes.filter(activo=True))
    if sedes_activas:
        total = len(sedes_activas)
        completadas = sum(1 for s in sedes_activas if s.estado == 'completado')
        en_progreso = sum(1 for s in sedes_activas if s.estado == 'en_progreso')
        if completadas == total:
            nuevo_estado = 'completado'
        elif completadas > 0 or en_progreso > 0:
            nuevo_estado = 'en_progreso'
        else:
            nuevo_estado = 'pendiente'
        if proyecto.estado_proyecto != nuevo_estado:
            Proyecto.objects.filter(pk=proyecto.pk).update(estado_proyecto=nuevo_estado)

    if sede.estado == 'completado':
        admins = get_user_model().objects.filter(
            cargo__in=('administrador', 'gerente'), is_active=True
        )
        for admin in admins:
            # Evitar notificación duplicada
            ya_existe = Notificacion.objects.filter(
                destinatario=admin,
                sede=sede,
                tipo='sede_completada',
                leida=False,
            ).exists()
            if not ya_existe:
                Notificacion.objects.create(
                    destinatario=admin,
                    tipo='sede_completada',
                    mensaje=f'La sede "{sede.nombre}" del proyecto "{sede.proyecto.nombre}" fue completada al 100%.',
                    proyecto=sede.proyecto,
                    sede=sede,
                )

