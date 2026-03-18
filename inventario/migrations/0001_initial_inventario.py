"""
Migración inicial para el módulo inventario.
Las tablas ya existen en la BD (creadas originalmente por la app 'projects').
Se usa SeparateDatabaseAndState para registrar los modelos en el estado de Django
sin ejecutar DDL (CREATE TABLE) real.
"""
from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0028_auditmodel_deleted_by_todos_modelos'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # no tocar la BD
            state_operations=[
                migrations.CreateModel(
                    name='Proveedor',
                    fields=[],
                    options={'managed': False},
                ),
                migrations.CreateModel(
                    name='Insumo',
                    fields=[],
                    options={'managed': False},
                ),
                migrations.CreateModel(
                    name='Requiere',
                    fields=[],
                    options={'managed': False},
                ),
                migrations.CreateModel(
                    name='Realizar',
                    fields=[],
                    options={'managed': False},
                ),
            ],
        ),
    ]
