from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0009_proveedor_rubro_choices_insumo_stock_check'),
    ]

    operations = [
        # Renombrar celular → telefono (sin pérdida de datos)
        migrations.RenameField(
            model_name='proveedor',
            old_name='celular',
            new_name='telefono',
        ),
        # Actualizar verbose_name de nombre y telefono
        migrations.AlterField(
            model_name='proveedor',
            name='nombre',
            field=models.CharField(max_length=200, verbose_name='Razón Social / Nombre de la Empresa'),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='telefono',
            field=models.CharField(max_length=15, verbose_name='Teléfono de la Empresa'),
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='correo',
            field=models.EmailField(blank=True, max_length=100, verbose_name='Correo de la Empresa'),
        ),
        # Agregar campos del encargado (todos opcionales)
        migrations.AddField(
            model_name='proveedor',
            name='encargado_nombre',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='Nombre del Encargado'),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='encargado_cargo',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Cargo del Encargado'),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='encargado_celular',
            field=models.CharField(blank=True, default='', max_length=15, verbose_name='Celular del Encargado'),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='encargado_correo',
            field=models.EmailField(blank=True, default='', verbose_name='Correo del Encargado'),
        ),
    ]
