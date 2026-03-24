from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0005_pago_db_design_review'),
    ]

    operations = [
        # Eliminar campo estado de Pago (campo redundante: un Pago registrado siempre está confirmado)
        migrations.RemoveField(
            model_name='pago',
            name='estado',
        ),
        # Agregar número de referencia/comprobante (vacío por defecto)
        migrations.AddField(
            model_name='pago',
            name='numero_referencia',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='N° Referencia / Comprobante',
            ),
        ),
        # Índice en fecha de Pago para acelerar filtros y ordenamiento
        migrations.AlterField(
            model_name='pago',
            name='fecha',
            field=models.DateField(db_index=True, verbose_name='Fecha Pago'),
        ),
        # Índice en fecha de PagoEmpleado
        migrations.AlterField(
            model_name='pagoempleado',
            name='fecha',
            field=models.DateField(db_index=True, verbose_name='Fecha de Pago'),
        ),
        # Restricción: solo un saldo_final activo por contrato
        migrations.AddConstraint(
            model_name='pagoempleado',
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True, concepto='saldo_final'),
                fields=['contrato'],
                name='unique_pago_empleado_saldo_final_activo',
            ),
        ),
    ]
