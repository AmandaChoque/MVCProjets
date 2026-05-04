from decimal import Decimal
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from dateutil.relativedelta import relativedelta


class AuditModel(models.Model):
    created    = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True,     verbose_name="Fecha Actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Eliminación")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+', verbose_name="Eliminado por"
    )
    activo = models.BooleanField(default=True, db_index=True, verbose_name="Activo")

    class Meta:
        abstract = True


# ── Cliente ───────────────────────────────────────────────────────────────────

class ActiveClienteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Cliente(AuditModel):
    TIPO_CONTRATANTE_CHOICES = [
        ('empresa',        'Empresa'),
        ('personal',       'Personal'),
        ('entidad_publica','Entidad Pública'),
    ]
    ROL_CHOICES = [
        ('propietario',    'Propietario'),
        ('representante',  'Representante'),
        ('gerente',        'Gerente'),
        ('presidente_zona','Presidente de Zona'),
        ('encargado',      'Encargado'),
    ]

    rol_contacto      = models.CharField(max_length=50,  choices=ROL_CHOICES, default='propietario', verbose_name="Rol de Contacto")
    nit_ci            = models.CharField(max_length=20,  blank=True, default='', verbose_name="NIT/CI")
    nombre            = models.CharField(max_length=50,  verbose_name="Nombres")
    apellido_paterno  = models.CharField(max_length=50,  verbose_name="Apellido Paterno")
    apellido_materno  = models.CharField(max_length=50,  blank=True, default='', verbose_name="Apellido Materno")
    telefono          = models.CharField(max_length=15,  verbose_name="Número de Teléfono")
    correo            = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Correo Electrónico")
    direccion         = models.CharField(max_length=255, verbose_name="Dirección")
    tipo_contratante  = models.CharField(max_length=20,  choices=TIPO_CONTRATANTE_CHOICES, default='personal', verbose_name="Tipo Contratante")
    nombre_entidad    = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de la Entidad")

    objects     = ActiveClienteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        constraints = [
            models.UniqueConstraint(
                fields=['nit_ci'],
                condition=Q(activo=True) & ~Q(nit_ci=''),
                name='unique_nit_ci_activo_when_not_empty',
            )
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"

    def delete(self, using=None, keep_parents=False):
        self.activo    = False
        self.deleted_at = timezone.now()
        self.save()


# ── Proyecto (absorbe campos del contrato) ────────────────────────────────────

class Proyecto(AuditModel):
    PROJECT_STATUS_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado',  'Completado'),
    ]
    PROJECT_TYPE_CHOICES = [
        ('instalacion_nueva',     'Instalación Nueva'),
        ('ampliacion',            'Ampliación'),
        ('mantenimiento_externo', 'Mantenimiento Externo'),
        ('emergencia',            'Emergencia'),
    ]
    PAYMENT_STATE_CHOICES = [
        ('no_pagado', 'No pagado'),
        ('parcial',   'Pago parcial'),
        ('pagado',    'Pago completo'),
    ]

    codigo              = models.CharField(max_length=20,  unique=True, verbose_name="Código Proyecto")
    nombre              = models.CharField(max_length=200, unique=True, verbose_name="Nombre Proyecto")
    descripcion         = models.TextField(blank=True, verbose_name="Descripción Proyecto")
    objetivo_general    = models.CharField(max_length=500, blank=True, default='', verbose_name="Objetivo General")
    descripcion_alcance = models.TextField(blank=True, default='', verbose_name="Alcance del Proyecto")
    acta_inicio         = models.FileField(upload_to='actas/', null=True, blank=True, verbose_name="Acta de Inicio")
    estado_proyecto     = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='pendiente', db_index=True, verbose_name="Estado Proyecto")
    tipo_proyecto       = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES,  default='instalacion_nueva', db_index=True, verbose_name="Tipo Proyecto")
    fecha_inicio        = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin           = models.DateField(null=True, blank=True, verbose_name="Fecha de Finalización")
    observacion         = models.TextField(blank=True, default='', verbose_name="Observación")
    estado_pago         = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', db_index=True, verbose_name="Estado de Pago")
    creado_por          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    cliente             = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name="Contratista")
    monto_total         = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Monto Total del Proyecto")
    equipo              = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='proyectos_asignados', verbose_name="Equipo del Proyecto",
    )

    # ── Campos de contrato absorbidos ─────────────────────────────────────────
    fecha_fin_contrato      = models.DateField(null=True, blank=True, verbose_name="Fecha Límite (Contrato)")
    monto_acordado          = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Monto Acordado (Bs.)")
    porcentaje_multa_diaria = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name="% Multa Diaria",
    )
    porcentaje_multa_maxima = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('20'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name="% Multa Máxima (tope)",
    )
    garantia_meses = models.PositiveSmallIntegerField(default=0, verbose_name="Meses de Garantía")
    documento_contrato = models.FileField(upload_to='contratos/', null=True, blank=True, verbose_name="Documento Contrato")

    # ── PMBOK §11 — Gestión de Riesgos ───────────────────────────────────────
    NIVEL_RIESGO_CHOICES = [
        ('bajo',  'Bajo'),
        ('medio', 'Medio'),
        ('alto',  'Alto'),
    ]
    nivel_riesgo      = models.CharField(max_length=10, choices=NIVEL_RIESGO_CHOICES, default='bajo', verbose_name="Nivel de Riesgo")
    descripcion_riesgo = models.TextField(blank=True, default='', verbose_name="Descripción del Riesgo / Plan de Mitigación")

    class Meta:
        verbose_name        = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        db_table            = 'projects_project'
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_inicio__isnull=True) | Q(fecha_fin__gte=models.F('fecha_inicio')),
                name='proyecto_fecha_fin_gte_inicio',
            ),
            models.CheckConstraint(
                condition=Q(monto_total__gte=0),
                name='proyecto_monto_total_no_negativo',
            ),
        ]

    def __str__(self):
        return self.nombre

    # ── Propiedades de contrato/multa ─────────────────────────────────────────

    @property
    def dias_retraso(self):
        if self.estado_proyecto == 'completado' or not self.fecha_fin_contrato:
            return 0
        hoy = date.today()
        return max((hoy - self.fecha_fin_contrato).days, 0)

    @property
    def multa_acumulada(self):
        if self.dias_retraso == 0 or not self.porcentaje_multa_diaria or not self.monto_acordado:
            return Decimal('0')
        multa_sin_tope = (self.porcentaje_multa_diaria / Decimal('100')) * self.monto_acordado * self.dias_retraso
        tope = (self.porcentaje_multa_maxima / Decimal('100')) * self.monto_acordado
        return min(multa_sin_tope, tope)

    @property
    def multa_tope_alcanzado(self):
        if self.dias_retraso == 0 or not self.porcentaje_multa_diaria or not self.monto_acordado:
            return False
        multa_sin_tope = (self.porcentaje_multa_diaria / Decimal('100')) * self.monto_acordado * self.dias_retraso
        tope = (self.porcentaje_multa_maxima / Decimal('100')) * self.monto_acordado
        return multa_sin_tope >= tope

    @property
    def estado_multa(self):
        if self.dias_retraso == 0:
            return 'normal'
        if self.multa_tope_alcanzado:
            return 'critico'
        return 'en_multa'

    # ── Propiedades de garantía ───────────────────────────────────────────────

    @property
    def garantia_fecha_vencimiento(self):
        if not self.garantia_meses or not self.fecha_fin:
            return None
        return self.fecha_fin + relativedelta(months=self.garantia_meses)

    @property
    def garantia_estado(self):
        venc = self.garantia_fecha_vencimiento
        if not venc:
            return None
        hoy = date.today()
        if hoy > venc:
            return 'vencida'
        if (venc - hoy).days <= 30:
            return 'por_vencer'
        return 'vigente'

    # ── Pago ──────────────────────────────────────────────────────────────────

    def _sync_estado_pago(self):
        totals = self.pagos.filter(activo=True, estado='pagado').aggregate(
            total_monto=Sum('monto'), total_descuento=Sum('descuento'),
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


# ── Sede (punto de instalación) ───────────────────────────────────────────────

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

    class Meta:
        verbose_name        = 'Sede de Instalación'
        verbose_name_plural = 'Sedes de Instalación'
        ordering            = ['nombre']

    def __str__(self):
        return f"{self.nombre} — {self.proyecto.nombre}"

    @property
    def porcentaje_checklist(self):
        total = self.tareas.filter(activo=True).count()
        if total == 0:
            return 0
        completadas = self.tareas.filter(activo=True, completado=True).count()
        return round(completadas / total * 100)

    def _sync_estado(self):
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


# ── Tarea de checklist por sede ───────────────────────────────────────────────

class TareaChecklist(AuditModel):
    sede                = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='tareas', verbose_name="Sede")
    descripcion         = models.CharField(max_length=255, verbose_name="Tarea")
    orden               = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")
    completado          = models.BooleanField(default=False, verbose_name="Completado")
    fecha_completado    = models.DateTimeField(null=True, blank=True, verbose_name="Fecha completado")
    completado_por      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name="Completado por"
    )
    participantes       = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='tareas_participadas', verbose_name="Participantes"
    )
    criterio_aceptacion = models.CharField(max_length=255, blank=True, default='', verbose_name="Criterio de Aceptación")

    class Meta:
        verbose_name        = 'Tarea Checklist'
        verbose_name_plural = 'Tareas Checklist'
        ordering            = ['orden', 'created']
        constraints = [
            models.CheckConstraint(
                condition=~Q(completado=True) | Q(completado_por__isnull=False),
                name='tarea_completado_por_requerido_si_completado',
            ),
        ]

    def __str__(self):
        estado = '✓' if self.completado else '○'
        return f"{estado} {self.descripcion} — {self.sede.nombre}"


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
        db_table            = 'projects_pagoproyecto'
        ordering            = ['-fecha']
        constraints = [
            models.CheckConstraint(condition=models.Q(monto__gt=0),      name='pago_monto_positivo'),
            models.CheckConstraint(condition=models.Q(descuento__gte=0), name='pago_descuento_no_negativo'),
        ]

    @property
    def monto_neto(self):
        return self.monto + self.descuento

    def __str__(self):
        if self.descuento:
            return f"Pago de {self.monto} + descuento {self.descuento} = {self.monto_neto} Bs."
        return f"Pago de {self.monto} Bs. ({self.get_tipo_pago_display()})"


# ── Señales ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender='projects.PagoProyecto')
@receiver(post_delete, sender='projects.PagoProyecto')
def update_project_payment_status(sender, instance, **kwargs):
    instance.proyecto._sync_estado_pago()


def _saldo_pendiente_proyecto(proyecto):
    totals = proyecto.pagos.filter(activo=True, estado='pagado').aggregate(
        t=Sum('monto'), td=Sum('descuento')
    )
    cubierto = (totals['t'] or Decimal('0')) + (totals['td'] or Decimal('0'))
    return max(Decimal('0'), proyecto.monto_total - cubierto)


def _aplicar_pago_pendiente_proyecto(proyecto, estado_nuevo):
    if estado_nuevo == 'completado':
        if not proyecto.pagos.filter(activo=True, estado='pendiente').exists():
            saldo = _saldo_pendiente_proyecto(proyecto)
            if saldo > 0:
                PagoProyecto.objects.create(
                    proyecto=proyecto,
                    monto=saldo,
                    fecha=date.today(),
                    tipo_pago='efectivo',
                    estado='pendiente',
                )
    else:
        proyecto.pagos.filter(activo=True, estado='pendiente').update(activo=False)


@receiver(post_save, sender=Proyecto)
def sync_pago_pendiente_proyecto(sender, instance, **kwargs):
    _aplicar_pago_pendiente_proyecto(instance, instance.estado_proyecto)


@receiver(post_save, sender=TareaChecklist)
def sincronizar_sede_y_proyecto(sender, instance, **kwargs):
    if not instance.activo:
        return
    sede = instance.sede
    sede._sync_estado()
    sede.refresh_from_db(fields=['estado'])

    proyecto = sede.proyecto
    sedes_activas = list(proyecto.sedes.filter(activo=True))
    if not sedes_activas:
        return

    total       = len(sedes_activas)
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
        hoy = timezone.now().date()
        if nuevo_estado == 'en_progreso' and not proyecto.fecha_inicio:
            update_fields['fecha_inicio'] = hoy
        if nuevo_estado == 'completado' and not proyecto.fecha_fin:
            update_fields['fecha_fin'] = hoy
        Proyecto.objects.filter(pk=proyecto.pk).update(**update_fields)
        _aplicar_pago_pendiente_proyecto(proyecto, nuevo_estado)
