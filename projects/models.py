from decimal import Decimal
from datetime import date

from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from django.db.models import Sum
from dateutil.relativedelta import relativedelta
from django.apps import apps
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
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Modificado por"
    )
    activo = models.BooleanField(default=True, db_index=True, verbose_name="Activo")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = getattr(self, '_modified_by', None)
        if user is not None:
            self.modificado_por = user
            update_fields = kwargs.get('update_fields')
            if update_fields is not None and 'modificado_por' not in update_fields:
                kwargs['update_fields'] = list(update_fields) + ['modificado_por']
        super().save(*args, **kwargs)


# Contratante
# custom manager to return only active clients by default
class ActiveClienteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Cliente(AuditModel):

    TIPO_CONTRATANTE_CHOICES = [
        ('personal', 'Personal / Negocio'),
        ('entidad_publica', 'Entidad Pública'),
    ]

    ROL_CHOICES = [
        ('propietario', 'Propietario'),
        ('encargado', 'Encargado'),
        ('gerente', 'Gerente'),
        ('representante', 'Representante'),
    ]

    rol_contacto = models.CharField(max_length=50, choices=ROL_CHOICES, default='propietario', verbose_name="Rol de Contacto")
    nit_ci = models.CharField(max_length=20, blank=True, default='', verbose_name="NIT/CI")
    nombre = models.CharField(max_length=50, verbose_name="Nombres")
    apellido_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=50, blank=True, default='', verbose_name="Apellido Materno")
    telefono = models.CharField(max_length=15, verbose_name="Número de Teléfono")
    correo = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Correo Electrónico")
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    tipo_contratante = models.CharField(max_length=20, choices=TIPO_CONTRATANTE_CHOICES, default='personal', verbose_name="Tipo Contratante")
    # Solo para tipo_contratante = 'entidad_publica'
    nombre_entidad = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de la Entidad")

    # managers
    objects = ActiveClienteManager()           # default manager filters activo=True
    all_objects = models.Manager()             # explicit manager returning all rows

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        constraints = [
            # Solo aplica para registros activos: evita colisiones entre clientes
            # soft-deleted que compartían el mismo NIT/CI
            models.UniqueConstraint(
                fields=['nit_ci'],
                condition=Q(activo=True) & ~Q(nit_ci=''),
                name='unique_nit_ci_activo_when_not_empty',
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"

    def delete(self, using=None, keep_parents=False):
        """Soft-delete: marca el cliente como inactivo en lugar de eliminarlo de la BD."""
        self.activo = False
        self.deleted_at = timezone.now()
        self.save()


# Proyecto
class Proyecto(AuditModel):
    PROJECT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    PROJECT_TYPE_CHOICES = [
        ('instalacion_nueva',     'Instalación Nueva'),
        ('mantenimiento_externo', 'Mantenimiento Externo'),
    ]
    # Opciones para el estado del pago
    PAYMENT_STATE_CHOICES = [
        ('no_pagado', 'No pagado'),
        ('parcial', 'Pago parcial'),
        ('pagado', 'Pago completo'),
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
    # por la señal post_save/post_delete de PagoProyecto. Nunca modificar directamente.
    estado_pago = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', db_index=True, verbose_name="Estado de Pago")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    # PROTECT evita borrar un cliente que tenga proyectos asociados (previene pérdida de datos)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Contratista")

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
        Recalcula y persiste el campo estado_pago considerando solo pagos confirmados
        (estado='pagado'). Usa .update() para no disparar señales post_save en Proyecto.
        """
        totals = self.pagos.filter(activo=True, estado='pagado').aggregate(
            total_monto=Sum('monto'),
            total_descuento=Sum('descuento'),
        )
        total_cubierto = (totals['total_monto'] or 0) + (totals['total_descuento'] or 0)

        if total_cubierto >= self.monto_total:
            nuevo_estado = 'pagado'
        elif total_cubierto > 0:
            nuevo_estado = 'parcial'
        else:
            nuevo_estado = 'no_pagado'

        self.estado_pago = nuevo_estado
        Proyecto.objects.filter(pk=self.pk).update(estado_pago=nuevo_estado)

# ── Cronograma planificado por empleado en el proyecto ───────────────────────

class AsignacionProyecto(AuditModel):
    """Cronograma planificado de un empleado en un proyecto (no reemplaza el M2M equipo)."""
    proyecto          = models.ForeignKey('Proyecto', on_delete=models.CASCADE, related_name='asignaciones', verbose_name="Proyecto")
    empleado          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='asignaciones_proyecto', verbose_name="Empleado")
    fecha_inicio_plan = models.DateField(null=True, blank=True, verbose_name="Inicio planificado")
    fecha_fin_plan    = models.DateField(null=True, blank=True, verbose_name="Fin planificado")
    dias_planificados = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Días planificados")

    class Meta:
        verbose_name        = 'Asignación de proyecto'
        verbose_name_plural = 'Asignaciones de proyecto'
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'empleado'],
                condition=Q(activo=True),
                name='unique_asignacion_activa_por_proyecto_empleado',
            ),
            models.CheckConstraint(
                condition=(
                    Q(fecha_fin_plan__isnull=True) |
                    Q(fecha_inicio_plan__isnull=True) |
                    Q(fecha_fin_plan__gte=models.F('fecha_inicio_plan'))
                ),
                name='asignacion_fecha_fin_gte_inicio',
            ),
        ]

    def __str__(self):
        return f"{self.empleado} en {self.proyecto}"

    @property
    def dias_reales(self):
        from empleados.models import JornadaEmpleado
        result = JornadaEmpleado.objects.filter(
            proyecto=self.proyecto,
            contrato__empleado=self.empleado,
            estado='aprobada',
            activo=True,
        ).aggregate(total=Sum('dias'))['total']
        return result or 0

    @property
    def eficiencia_pct(self):
        """Días planificados / días reales × 100. >100% = terminó antes, <100% = se pasó."""
        reales = self.dias_reales
        if self.dias_planificados and reales:
            return round((float(self.dias_planificados) / float(reales)) * 100, 1)
        return None

    @property
    def dias_retraso(self):
        if self.fecha_fin_plan:
            hoy = date.today()
            return max((hoy - self.fecha_fin_plan).days, 0)
        return 0

    @property
    def estado_asignacion(self):
        """
        Estado calculado al vuelo según fechas y avance real.
        completada  → proyecto completado o días reales >= días planificados
        vencida     → fecha_fin_plan ya pasó y no está completada
        por_vencer  → quedan ≤ 5 días para fecha_fin_plan
        en_curso    → dentro del rango de fechas
        pendiente   → fecha_inicio_plan aún no llegó (o sin fechas)
        """
        hoy = date.today()
        if self.proyecto.estado_proyecto == 'cancelado':
            return 'cancelado'
        if self.proyecto.estado_proyecto == 'completado':
            return 'completada'
        if self.dias_planificados and self.dias_reales >= self.dias_planificados:
            return 'completada'
        if self.fecha_fin_plan:
            if hoy > self.fecha_fin_plan:
                return 'vencida'
            if (self.fecha_fin_plan - hoy).days <= 5:
                return 'por_vencer'
        if self.fecha_inicio_plan and hoy >= self.fecha_inicio_plan:
            return 'en_curso'
        return 'pendiente'

    @property
    def pct_avance(self):
        """Porcentaje de días reales sobre días planificados (máx 100)."""
        if self.dias_planificados and self.dias_planificados > 0:
            return min(round((self.dias_reales / self.dias_planificados) * 100), 100)
        return 0


# Contrato entre la empresa y el cliente por proyecto
class ContratoProyecto(AuditModel):
    proyecto       = models.ForeignKey('Proyecto', on_delete=models.CASCADE, related_name='contratos', verbose_name="Proyecto")
    fecha_firma    = models.DateField(verbose_name="Fecha de Firma")
    fecha_inicio   = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin      = models.DateField(verbose_name="Fecha de Fin")
    monto_acordado          = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Acordado (Bs.)")
    porcentaje_multa_diaria = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        verbose_name="% Multa Diaria",
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    porcentaje_multa_maxima = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('20'),
        verbose_name="% Multa Máxima (tope)",
        help_text="Tope máximo de multa acumulada como % del monto acordado. Al superarlo el estado pasa a 'crítico'.",
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    garantia_meses = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Meses de Garantía",
        help_text="Meses de garantía incluidos en este contrato (0 = sin garantía).",
    )
    observaciones  = models.TextField(blank=True, verbose_name="Observaciones")
    documento      = models.FileField(upload_to='contratos/', null=True, blank=True, verbose_name="Documento")

    class Meta:
        verbose_name = 'Contrato de Proyecto'
        verbose_name_plural = 'Contratos de Proyectos'
        ordering = ['-created']
        constraints = [
            models.CheckConstraint(condition=Q(fecha_fin__gte=models.F('fecha_inicio')), name='contrato_proy_fecha_fin_gte_inicio'),
            models.CheckConstraint(condition=Q(fecha_firma__lte=models.F('fecha_inicio')), name='contrato_proy_fecha_firma_lte_inicio'),
            models.UniqueConstraint(fields=['proyecto'], condition=Q(activo=True), name='unique_contrato_proyecto_activo'),
            models.CheckConstraint(condition=Q(monto_acordado__gt=0), name='contrato_proy_monto_positivo'),
        ]

    def __str__(self):
        return f"Contrato proyecto — {self.proyecto.nombre}"

    @property
    def dias_retraso(self):
        """
        Días de retraso respecto a la fecha pactada en el contrato.
        - Proyecto completado: usa la fecha real de entrega (proyecto.fecha_fin) para
          conservar la multa acumulada al momento de cierre, aunque pase el tiempo.
        - Proyecto cancelado: sin penalización.
        - En curso: días corridos desde fecha_fin del contrato hasta hoy.
        """
        estado = self.proyecto.estado_proyecto
        if estado == 'cancelado':
            return 0
        hoy = date.today()
        if estado == 'completado':
            fecha_entrega = self.proyecto.fecha_fin or hoy
            if fecha_entrega > self.fecha_fin:
                return (fecha_entrega - self.fecha_fin).days
            return 0
        if hoy > self.fecha_fin:
            return (hoy - self.fecha_fin).days
        return 0

    @property
    def multa_acumulada(self):
        """
        Monto de multa acumulada en Bs. (días × % diario × monto_acordado),
        con tope en porcentaje_multa_maxima % del monto acordado.
        """
        if self.dias_retraso == 0 or not self.porcentaje_multa_diaria:
            return Decimal('0')
        multa_sin_tope = (self.porcentaje_multa_diaria / Decimal('100')) * self.monto_acordado * self.dias_retraso
        tope = (self.porcentaje_multa_maxima / Decimal('100')) * self.monto_acordado
        return min(multa_sin_tope, tope)

    @property
    def multa_tope_alcanzado(self):
        """True si la multa ya llegó al tope máximo definido en el contrato."""
        if self.dias_retraso == 0 or not self.porcentaje_multa_diaria:
            return False
        multa_sin_tope = (self.porcentaje_multa_diaria / Decimal('100')) * self.monto_acordado * self.dias_retraso
        tope = (self.porcentaje_multa_maxima / Decimal('100')) * self.monto_acordado
        return multa_sin_tope >= tope

    @property
    def porcentaje_multa_sobre_contrato(self):
        """% que representa la multa acumulada sobre el monto acordado."""
        if not self.monto_acordado:
            return Decimal('0')
        return (self.multa_acumulada / self.monto_acordado) * Decimal('100')

    @property
    def estado_multa(self):
        """'normal' sin retraso, 'en_multa' con retraso activo, 'critico' si alcanzó el tope."""
        if self.dias_retraso == 0:
            return 'normal'
        if self.multa_tope_alcanzado:
            return 'critico'
        return 'en_multa'


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
        verbose_name = 'Historial Contrato'
        verbose_name_plural = 'Historiales de Contrato'
        db_table = 'projects_historialpresupuesto'

    def __str__(self):
        return f"Presupuesto modificado — {self.fecha_modificacion}"


# Auditoría de cambios de estado del proyecto
class HistorialEstadoProyecto(models.Model):
    ESTADO_CHOICES = [
        ('pendiente',    'Pendiente'),
        ('en_progreso',  'En Progreso'),
        ('completado',   'Completado'),
        ('cancelado',    'Cancelado'),
    ]
    proyecto         = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='historial_estado', verbose_name="Proyecto")
    estado_anterior  = models.CharField(max_length=20, choices=ESTADO_CHOICES, verbose_name="Estado Anterior")
    estado_nuevo     = models.CharField(max_length=20, choices=ESTADO_CHOICES, verbose_name="Estado Nuevo")
    cambiado_por     = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+', verbose_name="Cambiado por"
    )
    fecha            = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    motivo           = models.TextField(blank=True, default='', verbose_name="Motivo / Observación")

    class Meta:
        verbose_name        = 'Historial de Estado'
        verbose_name_plural = 'Historial de Estados'
        db_table            = 'projects_historialestadoproyecto'
        ordering            = ['-fecha']

    def __str__(self):
        return f"{self.proyecto.nombre}: {self.estado_anterior} → {self.estado_nuevo} ({self.fecha:%d/%m/%Y})"


@receiver(pre_save, sender=Proyecto)
def registrar_cambio_estado_proyecto(sender, instance, **kwargs):
    """Registra en HistorialEstadoProyecto cuando cambia estado_proyecto manualmente."""
    if not instance.pk:
        return
    try:
        anterior = Proyecto.objects.get(pk=instance.pk)
    except Proyecto.DoesNotExist:
        return
    if anterior.estado_proyecto != instance.estado_proyecto:
        HistorialEstadoProyecto.objects.create(
            proyecto=anterior,
            estado_anterior=anterior.estado_proyecto,
            estado_nuevo=instance.estado_proyecto,
            cambiado_por=getattr(instance, '_current_user', None),
            motivo=getattr(instance, '_motivo_cambio_estado', ''),
        )
        # Bandera para fijar la fecha real de entrega en post_save
        instance._cambio_a_completado = (instance.estado_proyecto == 'completado')


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
        totals = instance.pagos.filter(activo=True, estado='pagado').aggregate(
            total_monto=Sum('monto'),
            total_descuento=Sum('descuento'),
        )
        total_cubierto = (totals['total_monto'] or 0) + (totals['total_descuento'] or 0)
        if total_cubierto >= instance.monto_total:
            nuevo_estado = 'pagado'
        elif total_cubierto > 0:
            nuevo_estado = 'parcial'
        else:
            nuevo_estado = 'no_pagado'
        if instance.estado_pago != nuevo_estado:
            Proyecto.objects.filter(pk=instance.pk).update(estado_pago=nuevo_estado)


# ── Plantilla de tareas para instalaciones ───────────────────────────────────

class PlantillaTarea(AuditModel):
    TIPO_CHOICES = [
        ('camara_ip',        'Cámara IP'),
        ('camara_analogica', 'Cámara Analógica'),
        ('dvr_nvr',          'DVR / NVR'),
        ('alarma',           'Sistema de Alarma'),
        ('sensor',           'Sensores'),
        ('otro',             'Otro'),
    ]

    nombre      = models.CharField(max_length=200, verbose_name="Nombre de la plantilla")
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de instalación")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = 'Plantilla de Tareas'
        verbose_name_plural = 'Plantillas de Tareas'
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.nombre}"


class ItemPlantilla(models.Model):
    plantilla   = models.ForeignKey(PlantillaTarea, on_delete=models.CASCADE, related_name='items', verbose_name="Plantilla")
    descripcion = models.CharField(max_length=255, verbose_name="Tarea")
    orden       = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")

    class Meta:
        verbose_name = 'Item de Plantilla'
        verbose_name_plural = 'Items de Plantilla'
        ordering = ['orden']

    def __str__(self):
        return f"{self.orden}. {self.descripcion}"


class SubItemPlantilla(models.Model):
    item        = models.ForeignKey(ItemPlantilla, on_delete=models.CASCADE, related_name='subitems', verbose_name="Tarea padre")
    descripcion = models.CharField(max_length=255, verbose_name="Subtarea")
    orden       = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")

    class Meta:
        verbose_name = 'Sub-ítem de Plantilla'
        verbose_name_plural = 'Sub-ítems de Plantilla'
        ordering = ['orden']

    def __str__(self):
        return f"  └ {self.descripcion}"


# ── Sede (punto de instalación dentro de un proyecto) ────────────────────────

class Sede(AuditModel):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado',  'Completado'),
    ]

    proyecto    = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='sedes', verbose_name="Proyecto")
    nombre      = models.CharField(max_length=200, verbose_name="Referencia del lugar")
    direccion   = models.CharField(max_length=500, verbose_name="Dirección")
    descripcion = models.TextField(blank=True, verbose_name="Descripción / Indicaciones")
    latitud     = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Latitud")
    longitud    = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="Longitud")
    estado      = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    plantilla   = models.ForeignKey(
        PlantillaTarea, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
        verbose_name="Plantilla de tareas",
    )

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
        return f"Foto — {self.sede.nombre} ({timezone.localtime(self.created).date() if self.created else ''})"


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
    participantes     = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='tareas_participadas', verbose_name="Participantes"
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


class SubtareaChecklist(AuditModel):
    tarea            = models.ForeignKey(TareaChecklist, on_delete=models.CASCADE, related_name='subtareas', verbose_name="Tarea")
    descripcion      = models.CharField(max_length=255, verbose_name="Subtarea")
    orden            = models.PositiveSmallIntegerField(default=1, verbose_name="Orden")
    completado       = models.BooleanField(default=False, verbose_name="Completado")
    fecha_completado = models.DateTimeField(null=True, blank=True, verbose_name="Fecha completado")
    completado_por   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="Completado por"
    )

    class Meta:
        verbose_name = 'Subtarea'
        verbose_name_plural = 'Subtareas'
        ordering = ['orden', 'created']

    def __str__(self):
        return f"  └ {'✓' if self.completado else '○'} {self.descripcion}"


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

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sede_id and self.proyecto_id and self.sede.proyecto_id != self.proyecto_id:
            raise ValidationError('El proyecto de la notificación no coincide con el proyecto de la sede.')

    def __str__(self):
        return f"[{self.tipo}] → {self.destinatario.username}: {self.mensaje[:60]}"


# ── Señal: al completar todas las tareas de una sede, notificar a admins/gerentes ──

# ── Pago del cliente al proyecto ─────────────────────────────────────────────

METODOS_PAGO = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
]


class PagoProyecto(AuditModel):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado',    'Pagado'),
    ]

    monto             = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto recibido (Bs.)")
    descuento         = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Descuento / Multa aplicada (Bs.)")
    motivo_descuento  = models.CharField(max_length=300, blank=True, default='', verbose_name="Motivo del descuento")
    fecha             = models.DateField(db_index=True, verbose_name="Fecha de Pago")
    tipo_pago         = models.CharField(max_length=15, choices=METODOS_PAGO, default='efectivo', verbose_name="Método de Pago")
    numero_referencia = models.CharField(max_length=100, blank=True, default='', verbose_name="N° Referencia / Comprobante")
    proyecto          = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='pagos', verbose_name="Proyecto")
    estado            = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pagado', verbose_name="Estado")

    class Meta:
        verbose_name_plural = 'Pagos'
        db_table = 'projects_pagoproyecto'
        ordering = ['-fecha']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='pago_monto_positivo',
            ),
            models.CheckConstraint(
                condition=models.Q(descuento__gte=0),
                name='pago_descuento_no_negativo',
            ),
        ]

    @property
    def monto_neto(self):
        """Monto efectivamente cubierto = dinero recibido + descuento/multa aplicada."""
        return self.monto + self.descuento

    def __str__(self):
        if self.descuento:
            return f"Pago de {self.monto} + descuento {self.descuento} = {self.monto_neto} Bs. ({self.get_tipo_pago_display()})"
        return f"Pago de {self.monto} Bs. ({self.get_tipo_pago_display()})"


@receiver(post_save, sender='projects.PagoProyecto')
@receiver(post_delete, sender='projects.PagoProyecto')
def update_project_payment_status(sender, instance, **kwargs):
    instance.proyecto._sync_estado_pago()


def _saldo_pendiente_proyecto(proyecto):
    """Retorna el saldo aún no cubierto por pagos confirmados (estado='pagado')."""
    totals = proyecto.pagos.filter(activo=True, estado='pagado').aggregate(
        t=Sum('monto'), td=Sum('descuento')
    )
    cubierto = (totals['t'] or Decimal('0')) + (totals['td'] or Decimal('0'))
    return max(Decimal('0'), proyecto.monto_total - cubierto)


# ── Señal: notificaciones de sede ────────────────────────────────────────────

# ── Garantía post-instalación ─────────────────────────────────────────────────

class Garantia(AuditModel):
    """
    Registro de garantía asociada a un ContratoProyecto.
    Se crea automáticamente cuando el proyecto pasa a 'completado'
    y su contrato activo tiene garantia_meses > 0.
    Los costos de reparación bajo garantía son absorbidos por SOBOTEC.
    """
    contrato          = models.OneToOneField(
        ContratoProyecto, on_delete=models.CASCADE,
        related_name='garantia', verbose_name="Contrato del proyecto"
    )
    fecha_inicio      = models.DateField(verbose_name="Inicio de garantía")
    fecha_vencimiento = models.DateField(verbose_name="Vencimiento de garantía")

    class Meta:
        verbose_name        = 'Garantía'
        verbose_name_plural = 'Garantías'
        ordering            = ['fecha_vencimiento']
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_vencimiento__gt=models.F('fecha_inicio')),
                name='garantia_vencimiento_posterior_inicio',
            ),
        ]

    def __str__(self):
        return f"Garantía — {self.contrato.proyecto.nombre} (vence {self.fecha_vencimiento:%d/%m/%Y})"

    @property
    def estado(self):
        hoy = date.today()
        if hoy > self.fecha_vencimiento:
            return 'vencida'
        if (self.fecha_vencimiento - hoy).days <= 30:
            return 'por_vencer'
        return 'vigente'

    @property
    def dias_restantes(self):
        return max((self.fecha_vencimiento - date.today()).days, 0)

    @property
    def costo_total_incidencias(self):
        return (
            self.incidencias.filter(activo=True)
            .aggregate(total=Sum('costo_reparacion'))['total'] or Decimal('0')
        )


class IncidenciaGarantia(AuditModel):
    """
    Fallo o avería reportada durante la vigencia de la garantía.
    El costo_reparacion es absorbido por SOBOTEC (no se cobra al cliente).
    """
    ESTADO_CHOICES = [
        ('pendiente',     'Pendiente'),
        ('en_reparacion', 'En Reparación'),
        ('resuelto',      'Resuelto'),
    ]

    garantia          = models.ForeignKey(
        Garantia, on_delete=models.CASCADE,
        related_name='incidencias', verbose_name="Garantía"
    )
    descripcion       = models.TextField(verbose_name="Descripción del problema")
    fecha_reporte     = models.DateField(verbose_name="Fecha del reporte")
    fecha_reparacion  = models.DateField(null=True, blank=True, verbose_name="Fecha de reparación")
    costo_reparacion  = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        verbose_name="Costo de reparación (Bs.)",
        help_text="Costo absorbido por SOBOTEC — no se cobra al cliente.",
    )
    reparado_por      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name="Atendido por"
    )
    estado            = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='pendiente', db_index=True, verbose_name="Estado"
    )
    evidencia         = models.FileField(
        upload_to='garantias/evidencias/',
        null=True, blank=True,
        verbose_name="Evidencia (foto o PDF)"
    )

    class Meta:
        verbose_name        = 'Incidencia de Garantía'
        verbose_name_plural = 'Incidencias de Garantía'
        ordering            = ['-fecha_reporte']
        constraints = [
            models.CheckConstraint(
                condition=Q(costo_reparacion__gte=0),
                name='incidencia_garantia_costo_no_negativo',
            ),
        ]

    def __str__(self):
        return f"Incidencia [{self.get_estado_display()}] — {self.garantia.contrato.proyecto.nombre} ({self.fecha_reporte})"


@receiver(post_save, sender=Proyecto)
def crear_garantia_al_completar(sender, instance, **kwargs):
    """
    Cuando un proyecto pasa a 'completado', si su contrato activo tiene
    garantia_meses > 0 y aún no existe una Garantia, la crea automáticamente.
    """
    if instance.estado_proyecto != 'completado':
        return
    contrato = instance.contratos.filter(activo=True).first()
    if not contrato or contrato.garantia_meses <= 0:
        return
    if hasattr(contrato, 'garantia'):
        return
    fecha_inicio      = instance.fecha_fin or date.today()
    fecha_vencimiento = fecha_inicio + relativedelta(months=contrato.garantia_meses)
    Garantia.objects.create(
        contrato=contrato,
        fecha_inicio=fecha_inicio,
        fecha_vencimiento=fecha_vencimiento,
    )


@receiver(post_save, sender=Proyecto)
def desactivar_contrato_al_cancelar(sender, instance, **kwargs):
    """Al cancelar un proyecto desactiva su ContratoProyecto activo (si existe)."""
    if instance.estado_proyecto != 'cancelado':
        return
    instance.contratos.filter(activo=True).update(activo=False, deleted_at=timezone.now())


@receiver(post_save, sender=Proyecto)
def fijar_fecha_fin_al_completar(sender, instance, **kwargs):
    """
    Cuando el proyecto se completa manualmente (via vista), fija fecha_fin
    a la fecha real de cierre para preservar el cómputo de multa.
    La vía por checklist ya actualiza fecha_fin directamente en notificar_sede_completada.
    """
    if instance.estado_proyecto == 'completado' and not instance.fecha_fin:
        Proyecto.objects.filter(pk=instance.pk).update(fecha_fin=date.today())


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
            update_fields = {'estado_proyecto': nuevo_estado}
            hoy = timezone.localdate()
            # Primer avance → fijar fecha_inicio del proyecto
            if nuevo_estado == 'en_progreso' and not proyecto.fecha_inicio:
                update_fields['fecha_inicio'] = hoy
            # Todas las sedes completadas → fijar la fecha real de entrega
            if nuevo_estado == 'completado':
                update_fields['fecha_fin'] = hoy
            Proyecto.objects.filter(pk=proyecto.pk).update(**update_fields)

    if sede.estado == 'completado':
        admins = list(get_user_model().objects.filter(
            cargo__in=('administrador', 'gerente'), is_active=True
        ))
        if admins:
            # Una sola consulta para saber quiénes ya tienen la notificación
            ya_notificados = set(Notificacion.objects.filter(
                destinatario__in=admins,
                sede=sede,
                tipo='sede_completada',
                leida=False,
            ).values_list('destinatario_id', flat=True))
            # bulk_create para los que aún no la tienen
            nuevas = [
                Notificacion(
                    destinatario=admin,
                    tipo='sede_completada',
                    mensaje=f'La sede "{sede.nombre}" del proyecto "{sede.proyecto.nombre}" fue completada al 100%.',
                    proyecto=sede.proyecto,
                    sede=sede,
                )
                for admin in admins if admin.pk not in ya_notificados
            ]
            if nuevas:
                Notificacion.objects.bulk_create(nuevas)


@receiver(post_save, sender=TareaChecklist)
def crear_jornada_al_completar_tarea(sender, instance, **kwargs):
    """
    Si la tarea se marca completada y tiene exactamente un participante,
    crea automáticamente una JornadaEmpleado pendiente para ese empleado.
    """
    if not instance.activo or not instance.completado:
        return

    participantes = list(instance.participantes.all())
    if len(participantes) != 1:
        return

    empleado = participantes[0]
    proyecto = instance.sede.proyecto
    fecha = instance.fecha_completado.date() if instance.fecha_completado else timezone.localdate()

    JornadaEmpleado = apps.get_model('empleados', 'JornadaEmpleado')
    ContratoEmpleado = apps.get_model('empleados', 'ContratoEmpleado')

    contrato = ContratoEmpleado.objects.filter(empleado=empleado, activo=True).first()
    if not contrato:
        return

    if fecha < contrato.fecha_inicio or fecha > contrato.fecha_fin:
        return

    sede_nombre = instance.sede.nombre or instance.sede.direccion
    observacion = f'Tarea completada: {instance.descripcion} (Sede: {sede_nombre})'

    JornadaEmpleado.objects.get_or_create(
        contrato=contrato,
        proyecto=proyecto,
        fecha=fecha,
        defaults={
            'dias': Decimal('1.0'),
            'observacion': observacion,
            'estado': 'pendiente',
            'registrado_por': instance.completado_por,
        }
    )
