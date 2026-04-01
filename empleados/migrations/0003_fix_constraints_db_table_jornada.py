from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empleados', '0002_initial'),
    ]

    operations = [
        # ── ContratoEmpleado: monto_acordado > 0 ─────────────────────────────
        migrations.AddConstraint(
            model_name='contratoempleado',
            constraint=models.CheckConstraint(
                condition=models.Q(monto_acordado__gt=0),
                name='contrato_emp_monto_positivo',
            ),
        ),

        # ── ContratoProyecto: monto_acordado > 0 ─────────────────────────────
        migrations.AddConstraint(
            model_name='contratoproyecto',
            constraint=models.CheckConstraint(
                condition=models.Q(monto_acordado__gt=0),
                name='contrato_proy_monto_positivo',
            ),
        ),

        # ── PagoEmpleado: renombrar tabla de projects_ a empleados_ ───────────
        migrations.AlterModelTable(
            name='pagoempleado',
            table='empleados_pagoempleado',
        ),

        # ── JornadaEmpleado: dias solo puede ser 0.5 o 1.0 ───────────────────
        migrations.AddConstraint(
            model_name='jornadaempleado',
            constraint=models.CheckConstraint(
                condition=models.Q(dias=Decimal('0.5')) | models.Q(dias=Decimal('1.0')),
                name='jornada_dias_validos',
            ),
        ),

        # ── JornadaEmpleado: un solo registro activo por (contrato, proyecto, fecha) ──
        migrations.AddConstraint(
            model_name='jornadaempleado',
            constraint=models.UniqueConstraint(
                fields=['contrato', 'proyecto', 'fecha'],
                condition=models.Q(activo=True),
                name='unique_jornada_contrato_proyecto_fecha',
            ),
        ),
    ]
