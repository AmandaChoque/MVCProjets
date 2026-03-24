import django.db.models.deletion
import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0004_pagoempleado_contrato_protect'),
        ('projects', '0007_fix_quality_improvements'),
    ]

    operations = [
        # tipo_pago: parcial/completo → efectivo/transferencia
        migrations.AlterField(
            model_name='pago',
            name='tipo_pago',
            field=models.CharField(
                choices=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia')],
                default='efectivo',
                max_length=15,
                verbose_name='Método de Pago',
            ),
        ),
        # Migrar datos existentes: cualquier valor antiguo → efectivo
        migrations.RunSQL(
            sql="UPDATE projects_pago SET tipo_pago = 'efectivo' WHERE tipo_pago NOT IN ('efectivo', 'transferencia');",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # monto: max_digits 10 → 12
        migrations.AlterField(
            model_name='pago',
            name='monto',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Monto'),
        ),
        # proyecto: CASCADE → PROTECT
        migrations.AlterField(
            model_name='pago',
            name='proyecto',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagos',
                to='projects.proyecto',
                verbose_name='Proyecto',
            ),
        ),
        # CheckConstraint monto > 0 en Pago
        migrations.AddConstraint(
            model_name='pago',
            constraint=models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='pago_monto_positivo',
            ),
        ),
        # CheckConstraint monto > 0 en PagoEmpleado
        migrations.AddConstraint(
            model_name='pagoempleado',
            constraint=models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name='pagoempleado_monto_positivo',
            ),
        ),
    ]
