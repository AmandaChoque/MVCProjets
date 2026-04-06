from decimal import Decimal
from datetime import date

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator

from projects.models import AuditModel


METODOS_PAGO = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
]


class Empleado(AbstractUser):
    POSITION_CHOICES = [
        ('administrador',    'Administrador'),
        ('gerente',          'Gerente'),
        ('instalador',       'Supervisor'),
        ('tecnico_soporte',  'Técnico'),
        ('secretaria',       'Secretaria'),
    ]

    nombre           = models.CharField(max_length=100, verbose_name="Nombre")
    apellido_paterno = models.CharField(max_length=100, verbose_name="Apellido Paterno")
    apellido_materno = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apellido Materno")
    numero_celular   = models.CharField(max_length=15, blank=True, verbose_name="Numero Celular")
    cargo            = models.CharField(max_length=50, choices=POSITION_CHOICES, default='administrador', verbose_name="Cargo")
    carnet_identidad = models.CharField(max_length=20, unique=True, verbose_name="Carnet de Identidad")

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno or ''} - CI: {self.carnet_identidad}"


class ContratoEmpleado(AuditModel):
    empleado        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contratos_empleado', verbose_name="Empleado")
    dias_laborales  = models.PositiveIntegerField(default=28, verbose_name="Días laborales acordados",
                          validators=[MinValueValidator(1)])
    fecha_firma     = models.DateField(verbose_name="Fecha de Firma")
    fecha_inicio    = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin       = models.DateField(verbose_name="Fecha de Fin")
    monto_acordado  = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Acordado (Bs.)")
    observaciones   = models.TextField(blank=True, verbose_name="Observaciones")
    documento       = models.FileField(upload_to='contratos/', null=True, blank=True, verbose_name="Documento")

    class Meta:
        verbose_name = 'Contrato de Empleado'
        verbose_name_plural = 'Contratos de Empleados'
        ordering = ['-created']
        constraints = [
            models.CheckConstraint(condition=Q(fecha_fin__gte=models.F('fecha_inicio')), name='contrato_emp_fecha_fin_gte_inicio'),
            models.CheckConstraint(condition=Q(fecha_firma__lte=models.F('fecha_inicio')), name='contrato_emp_fecha_firma_lte_inicio'),
            models.UniqueConstraint(fields=['empleado'], condition=Q(activo=True), name='unique_contrato_empleado_activo'),
            models.CheckConstraint(condition=Q(monto_acordado__gt=0), name='contrato_emp_monto_positivo'),
            models.CheckConstraint(condition=Q(dias_laborales__gt=0), name='contrato_emp_dias_laborales_positivo'),
        ]

    def __str__(self):
        return f"Contrato — {self.empleado.nombre} {self.empleado.apellido_paterno}"

    @property
    def monto_diario(self):
        if self.monto_acordado and self.dias_laborales:
            return self.monto_acordado / Decimal(str(self.dias_laborales))
        return self.monto_acordado


class ContratoProyecto(AuditModel):
    proyecto       = models.ForeignKey('projects.Proyecto', on_delete=models.CASCADE, related_name='contratos', verbose_name="Proyecto")
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
        """Días corridos desde fecha_fin hasta hoy. 0 si el proyecto ya está completado o no hay retraso."""
        if self.proyecto.estado_proyecto == 'completado':
            return 0
        hoy = date.today()
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


class PagoEmpleado(AuditModel):
    CONCEPTO_CHOICES = [
        ('pago_jornada', 'Pago por jornada(s)'),
        ('adelanto',     'Adelanto'),
        ('liquidacion',  'Liquidación final'),
        ('dia_extra',    'Día extra fuera del contrato'),
        ('otro',         'Otro'),
    ]

    monto     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs.)")
    fecha     = models.DateField(db_index=True, verbose_name="Fecha de Pago")
    tipo_pago = models.CharField(max_length=15, choices=METODOS_PAGO, default='efectivo', verbose_name="Método de Pago")
    contrato  = models.ForeignKey(
        ContratoEmpleado, on_delete=models.PROTECT,
        related_name='pagos', verbose_name="Contrato"
    )
    concepto  = models.CharField(max_length=20, choices=CONCEPTO_CHOICES, verbose_name="Concepto")

    class Meta:
        verbose_name = 'Pago a Empleado'
        verbose_name_plural = 'Pagos a Empleados'
        ordering = ['-fecha']
        db_table = 'empleados_pagoempleado'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='pagoempleado_monto_positivo',
            ),
            models.UniqueConstraint(
                fields=['contrato'],
                condition=models.Q(activo=True, concepto='liquidacion'),
                name='unique_pago_empleado_liquidacion_activo',
            ),
        ]

    def __str__(self):
        return f"Bs. {self.monto} — {self.concepto} ({self.fecha})"


class AsignacionDiaria(AuditModel):
    """Registro de quién fue a trabajar, a qué proyecto/sede y en qué turno."""
    TURNO_CHOICES = [
        ('completo', 'Día completo (1.0)'),
        ('manana',   'Mañana — Medio día (0.5)'),
        ('tarde',    'Tarde — Medio día (0.5)'),
    ]

    fecha       = models.DateField(db_index=True, verbose_name="Fecha")
    proyecto    = models.ForeignKey(
        'projects.Proyecto', on_delete=models.PROTECT,
        related_name='asignaciones_diarias', verbose_name="Proyecto"
    )
    sede        = models.ForeignKey(
        'projects.Sede', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='asignaciones', verbose_name="Sede"
    )
    supervisor  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='asignaciones_supervisor', verbose_name="Supervisor"
    )
    instalador  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='asignaciones_instalador', verbose_name="Instalador"
    )
    turno       = models.CharField(max_length=10, choices=TURNO_CHOICES, default='completo', verbose_name="Turno")
    observacion = models.TextField(blank=True, verbose_name="Observación")
    tareas_realizadas = models.ManyToManyField(
        'projects.TareaChecklist', blank=True,
        related_name='asignaciones', verbose_name="Tareas realizadas"
    )

    class Meta:
        verbose_name = 'Asignación Diaria'
        verbose_name_plural = 'Asignaciones Diarias'
        ordering = ['-fecha']

    def __str__(self):
        equipo = ' / '.join(filter(None, [
            f"{self.supervisor.nombre} {self.supervisor.apellido_paterno}" if self.supervisor else None,
            f"{self.instalador.nombre} {self.instalador.apellido_paterno}" if self.instalador else None,
        ]))
        return f"{self.fecha} — {self.proyecto.nombre} — {equipo}"

    @property
    def dias(self):
        return Decimal('1.0') if self.turno == 'completo' else Decimal('0.5')


class JornadaEmpleado(AuditModel):
    """Registro diario de trabajo de un empleado: en qué proyecto trabajó y cuánto."""
    DIAS_CHOICES = [
        ('0.5', 'Medio día (0.5)'),
        ('1.0', 'Día completo (1.0)'),
    ]

    contrato = models.ForeignKey(
        ContratoEmpleado, on_delete=models.CASCADE,
        related_name='jornadas', verbose_name="Contrato"
    )
    proyecto = models.ForeignKey(
        'projects.Proyecto', on_delete=models.PROTECT,
        related_name='jornadas_empleados', verbose_name="Proyecto trabajado"
    )
    fecha = models.DateField(verbose_name="Fecha")
    dias  = models.DecimalField(
        max_digits=3, decimal_places=1, default=1.0,
        verbose_name="Días trabajados",
        validators=[MinValueValidator(0.5), MaxValueValidator(1.0)],
    )
    observacion = models.TextField(blank=True, verbose_name="Observación")
    pago = models.ForeignKey(
        PagoEmpleado,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='jornadas_cubiertas',
        verbose_name="Pago que cubre esta jornada",
    )
    asignacion = models.ForeignKey(
        AsignacionDiaria,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='jornadas',
        verbose_name="Asignación de origen",
    )

    class Meta:
        verbose_name = 'Jornada de Empleado'
        verbose_name_plural = 'Jornadas de Empleados'
        ordering = ['-fecha']
        constraints = [
            models.CheckConstraint(
                condition=Q(dias=Decimal('0.5')) | Q(dias=Decimal('1.0')),
                name='jornada_dias_validos',
            ),
            models.UniqueConstraint(
                fields=['contrato', 'proyecto', 'fecha'],
                condition=Q(activo=True),
                name='unique_jornada_contrato_proyecto_fecha',
            ),
        ]

    def __str__(self):
        emp = self.contrato.empleado
        return f"{emp.nombre} {emp.apellido_paterno} — {self.fecha} ({self.dias}d) — {self.proyecto.nombre}"

    @property
    def monto(self):
        return self.dias * self.contrato.monto_diario
