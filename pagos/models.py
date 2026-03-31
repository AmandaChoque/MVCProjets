from django.db import models
from django.db.models import Sum

from projects.models import AuditModel, Proyecto, Contrato

METODOS_PAGO = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
]


class PagoBase(AuditModel):
    """
    Clase base abstracta para todos los pagos del sistema.
    Centraliza los atributos comunes: monto, fecha y método de pago.
    Subclases: Pago (cliente→proyecto) y PagoEmpleado (empresa→empleado).
    """
    monto     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs.)")
    fecha     = models.DateField(db_index=True, verbose_name="Fecha de Pago")
    tipo_pago = models.CharField(max_length=15, choices=METODOS_PAGO, default='efectivo', verbose_name="Método de Pago")

    class Meta(AuditModel.Meta):
        abstract = True
        ordering = ['-fecha']


class Pago(PagoBase):
    numero_referencia  = models.CharField(max_length=100, blank=True, default='', verbose_name="N° Referencia / Comprobante")
    proyecto           = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='pagos', verbose_name="Proyecto")

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


class PagoEmpleado(PagoBase):
    CONCEPTO_CHOICES = [
        ('pago_jornada', 'Pago por jornada(s)'),
        ('adelanto',     'Adelanto'),
        ('liquidacion',  'Liquidación final'),
        ('dia_extra',    'Día extra fuera del contrato'),
        ('otro',         'Otro'),
    ]

    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='pagos', verbose_name="Contrato"
    )
    concepto = models.CharField(max_length=20, choices=CONCEPTO_CHOICES, verbose_name="Concepto")

    class Meta:
        verbose_name = 'Pago a Empleado'
        verbose_name_plural = 'Pagos a Empleados'
        ordering = ['-fecha']
        db_table = 'projects_pagoempleado'
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


# Señal: actualizar estado_pago del proyecto al guardar o eliminar un Pago
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Pago)
@receiver(post_delete, sender=Pago)
def update_project_payment_status(sender, instance, **kwargs):
    instance.proyecto._sync_estado_pago()
