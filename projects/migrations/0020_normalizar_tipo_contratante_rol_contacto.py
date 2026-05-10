from django.db import migrations


def normalizar_hacia_adelante(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE projects_cliente SET tipo_contratante='personal' WHERE tipo_contratante='empresa'"
        )
        cursor.execute(
            "UPDATE projects_cliente SET rol_contacto='representante' WHERE rol_contacto='presidente_zona'"
        )


def normalizar_hacia_atras(apps, schema_editor):
    pass  # reversión sin sentido: no sabemos qué era 'empresa' vs 'personal'


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0019_eliminar_emergencia_tipo_proyecto'),
    ]

    operations = [
        migrations.RunPython(normalizar_hacia_adelante, normalizar_hacia_atras),
    ]
