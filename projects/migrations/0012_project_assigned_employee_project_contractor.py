# Generated by Django 5.1.2 on 2024-12-12 02:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0011_alter_payment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='assigned_employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.employee', verbose_name='Empleado Asignado'),
        ),
        migrations.AddField(
            model_name='project',
            name='contractor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.contractor', verbose_name='Contratista'),
        ),
    ]