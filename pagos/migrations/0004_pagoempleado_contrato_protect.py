import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0003_fix_quality_improvements'),
        ('projects', '0007_fix_quality_improvements'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagoempleado',
            name='contrato',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagos',
                to='projects.contrato',
                verbose_name='Contrato',
            ),
        ),
        migrations.AlterModelOptions(
            name='pago',
            options={'ordering': ['-fecha'], 'verbose_name_plural': 'Pagos'},
        ),
    ]
