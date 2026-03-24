from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_fix_quality_improvements'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='historialpago',
            table='projects_historialpago',
        ),
    ]
