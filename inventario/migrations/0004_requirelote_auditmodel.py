import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campos AuditModel a RequiereLote para trazabilidad de asignaciones FIFO.
    Al editar un Requiere, los lotes anteriores quedan con activo=False en lugar de
    eliminarse físicamente, preservando el historial.
    """

    dependencies = [
        ('inventario', '0003_remove_sede_requiere_add_unique_lote'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='requierelote',
            name='activo',
            field=models.BooleanField(db_index=True, default=True, verbose_name='Activo'),
        ),
        migrations.AddField(
            model_name='requierelote',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Fecha Creación'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='requierelote',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Fecha Actualización'),
        ),
        migrations.AddField(
            model_name='requierelote',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha Eliminación'),
        ),
        migrations.AddField(
            model_name='requierelote',
            name='deleted_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Eliminado por',
            ),
        ),
        # Reemplazar la constraint sin condición por una que solo aplique a lotes activos
        migrations.RemoveConstraint(
            model_name='requierelote',
            name='unique_requiere_lote_requiere_compra',
        ),
        migrations.AddConstraint(
            model_name='requierelote',
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True),
                fields=('requiere', 'compra'),
                name='unique_requirelote_requiere_compra_activo',
            ),
        ),
    ]
