from django.db import models
from django.db.models import Sum

from projects.models import AuditModel, Proyecto, Contrato


class Pago(AuditModel):
    PAYMENT_STATUS_CHOICES = [
        ('pagado',    'Pagado'),
        ('pendiente', 'Pendiente'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('parcial',  'Parcial'),
        ('completo', 'Completo'),
    ]

    monto     = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    fecha     = models.DateField(verbose_name="Fecha Pago")
    estado    = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pagado', verbose_name="Estado Pago")
    tipo_pago = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='parcial', verbose_name="Tipo Pago")
    proyecto  = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='pagos', verbose_name="Proyecto")

    class Meta:
        verbose_name_plural = 'Pagos'
        db_table = 'projects_pago'

    def __str__(self):
        return f"Pago de {self.monto} - {self.estado}"

    def is_payment_complete(self):
        return self.monto >= self.proyecto.monto_total

    def update_payment_status(self):
        if self.monto >= self.proyecto.monto_total:
            self.estado = 'pagado'
        else:
            self.estado = 'pendiente'
        self.save()
        self.proyecto.update_payment_status()


class PagoEmpleado(AuditModel):
    CONCEPTO_CHOICES = [
        ('anticipo',    'Anticipo'),
        ('mensualidad', 'Mensualidad'),
        ('saldo_final', 'Saldo Final'),
        ('otro',        'Otro'),
    ]

    contrato = models.ForeignKey(
        Contrato, on_delete=models.CASCADE,
        related_name='pagos', verbose_name="Contrato"
    )
    monto    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto (Bs.)")
    fecha    = models.DateField(verbose_name="Fecha de Pago")
    concepto = models.CharField(max_length=20, choices=CONCEPTO_CHOICES, verbose_name="Concepto")

    class Meta:
        verbose_name = 'Pago a Empleado'
        verbose_name_plural = 'Pagos a Empleados'
        ordering = ['-fecha']
        db_table = 'projects_pagoempleado'

    def __str__(self):
        return f"Bs. {self.monto} — {self.concepto} ({self.fecha})"


# Señal: actualizar estado_pago del proyecto al guardar un Pago
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Pago)
def update_project_payment_status(sender, instance, **kwargs):
    instance.proyecto.update_payment_status()
