from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0011_requiere_lote_fifo'),
    ]

    operations = [
        # Renombrar Insumo.costo_unitario → ultimo_precio_compra
        migrations.RenameField(
            model_name='insumo',
            old_name='costo_unitario',
            new_name='ultimo_precio_compra',
        ),
        migrations.AlterField(
            model_name='insumo',
            name='ultimo_precio_compra',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='Último Precio Compra (Bs.)',
            ),
        ),
        # Agregar Compra.numero_factura
        migrations.AddField(
            model_name='compra',
            name='numero_factura',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='N° Factura / Comprobante',
            ),
        ),
    ]
