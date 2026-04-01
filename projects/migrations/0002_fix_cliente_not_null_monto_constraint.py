from django.db import migrations, models
import django.db.models.deletion


def eliminar_proyectos_sin_cliente(apps, schema_editor):
    """Elimina proyectos sin cliente asignado antes de hacer la columna NOT NULL."""
    Proyecto = apps.get_model('projects', 'Proyecto')
    huerfanos = Proyecto.objects.filter(cliente__isnull=True)
    count = huerfanos.count()
    if count:
        huerfanos.delete()
        print(f"\n  [migración] Se eliminaron {count} proyecto(s) sin cliente.")


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        # Paso 1: limpiar filas con cliente=NULL antes de aplicar NOT NULL
        migrations.RunPython(
            eliminar_proyectos_sin_cliente,
            reverse_code=migrations.RunPython.noop,
        ),

        # Paso 2: hacer cliente NOT NULL
        migrations.AlterField(
            model_name='proyecto',
            name='cliente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='projects.cliente',
                verbose_name='Contratista',
            ),
        ),

        # Paso 3: agregar constraint monto_total >= 0
        migrations.AddConstraint(
            model_name='proyecto',
            constraint=models.CheckConstraint(
                condition=models.Q(monto_total__gte=0),
                name='proyecto_monto_total_no_negativo',
            ),
        ),
    ]
