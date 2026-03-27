from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0006_remove_estado_add_numero_referencia'),
    ]

    operations = [
        # #5 — Agregar método de pago a PagoEmpleado (consistencia con Pago)
        migrations.AddField(
            model_name='pagoempleado',
            name='tipo_pago',
            field=models.CharField(
                choices=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia')],
                default='efectivo',
                max_length=15,
                verbose_name='Método de Pago',
            ),
        ),
    ]
