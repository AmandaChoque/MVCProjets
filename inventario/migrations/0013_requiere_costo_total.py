from django.db import migrations, models


def recalcular_costo_total(apps, schema_editor):
    Requiere = apps.get_model('inventario', 'Requiere')
    for r in Requiere.objects.all():
        r.costo_total = r.cantidad * r.costo_total  # field already renamed, was costo_unitario
        r.save(update_fields=['costo_total'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0012_compra_numero_factura_insumo_ultimo_precio'),
    ]

    operations = [
        migrations.RenameField(
            model_name='requiere',
            old_name='costo_unitario',
            new_name='costo_total',
        ),
        migrations.AlterField(
            model_name='requiere',
            name='costo_total',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Costo Total (Bs.)'),
        ),
        migrations.RunPython(recalcular_costo_total, migrations.RunPython.noop),
    ]
