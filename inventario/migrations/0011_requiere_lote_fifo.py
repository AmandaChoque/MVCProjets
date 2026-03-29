from django.db import migrations, models
import django.db.models.deletion


def aplicar_fifo_historico(apps, schema_editor):
    """
    Crea los RequiereLote para todos los Requiere activos existentes,
    aplicando FIFO retroactivamente por orden de creación.
    Si hay inconsistencias de stock no bloquea la migración — deja sin lotes
    los Requiere que no pudieron ser trazados.
    """
    Requiere     = apps.get_model('inventario', 'Requiere')
    Compra       = apps.get_model('inventario', 'Compra')
    RequiereLote = apps.get_model('inventario', 'RequiereLote')

    # disponibles[compra_pk] = cantidad aún no asignada a ningún lote
    disponibles = {}
    for compra in Compra.objects.filter(activo=True):
        disponibles[compra.pk] = compra.cantidad

    # Procesar requieres activos en orden de creación (más antiguo primero = FIFO)
    for requiere in Requiere.objects.filter(activo=True).order_by('created'):
        if requiere.insumo_id is None:
            continue

        compras_del_insumo = Compra.objects.filter(
            insumo_id=requiere.insumo_id,
            activo=True,
        ).order_by('fecha', 'created')

        restante = requiere.cantidad
        for compra in compras_del_insumo:
            if restante <= 0:
                break
            disp = disponibles.get(compra.pk, 0)
            if disp <= 0:
                continue
            tomar = min(disp, restante)
            RequiereLote.objects.create(
                requiere=requiere,
                compra=compra,
                cantidad=tomar,
                costo_unitario=compra.costo_unitario,
            )
            disponibles[compra.pk] -= tomar
            restante -= tomar
        # Si restante > 0 hay inconsistencia de datos — se ignora silenciosamente


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0010_proveedor_encargado'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequiereLote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(verbose_name='Cantidad consumida')),
                ('costo_unitario', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Costo unitario del lote')),
                ('compra', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lotes_asignados',
                    to='inventario.compra',
                    verbose_name='Lote de compra',
                )),
                ('requiere', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lotes',
                    to='inventario.requiere',
                    verbose_name='Requiere',
                )),
            ],
            options={
                'verbose_name': 'Lote FIFO',
                'verbose_name_plural': 'Lotes FIFO',
                'db_table': 'inventario_requiere_lote',
            },
        ),
        migrations.RunPython(aplicar_fifo_historico, migrations.RunPython.noop),
    ]
