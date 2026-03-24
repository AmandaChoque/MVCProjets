from django.db import models
from django.db.models import Sum

from projects.models import AuditModel, Proyecto, Contrato


class Pago(AuditModel):
    PAYMENT_TYPE_CHOICES = [
        ('efectivo',      'Efectivo'),
        ('transferencia', 'Transferencia'),
    ]

    monto              = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    fecha              = models.DateField(db_index=True, verbose_name="Fecha Pago")
    tipo_pago          = models.CharField(max_length=15, choices=PAYMENT_TYPE_CHOICES, default='efectivo', verbose_name="Método de Pago")
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


class PagoEmpleado(AuditModel):
    CONCEPTO_CHOICES = [
        ('anticipo',    'Anticipo'),
        ('mensualidad', 'Mensualidad'),
        ('saldo_final', 'Saldo Final'),
        ('otro',        'Otro'),
    ]

    contrato = models.ForeignKey(
        Contrato, on_delete=models.PROTECT,
        related_name='pagos', verbose_name="Contrato"
    )
    monto    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs.)")
    fecha    = models.DateField(db_index=True, verbose_name="Fecha de Pago")
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
                condition=models.Q(activo=True, concepto='saldo_final'),
                name='unique_pago_empleado_saldo_final_activo',
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
    instance.proyecto.update_payment_status()
