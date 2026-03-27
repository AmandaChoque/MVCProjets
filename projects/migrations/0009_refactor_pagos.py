from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_historialpago_db_table'),
    ]

    operations = [
        # #1 — Renombrar el modelo en el registro de Django
        migrations.RenameModel(
            old_name='HistorialPago',
            new_name='HistorialPresupuesto',
        ),
        # #1 — Renombrar la tabla física en la BD
        migrations.AlterModelTable(
            name='historialpresupuesto',
            table='projects_historialpresupuesto',
        ),
        # #4 — Consistencia de max_digits en monto_total
        migrations.AlterField(
            model_name='proyecto',
            name='monto_total',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=12,
                verbose_name='Monto Total del Proyecto'
            ),
        ),
    ]
