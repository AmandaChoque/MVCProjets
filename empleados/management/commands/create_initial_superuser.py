import os
from django.core.management.base import BaseCommand
from empleados.models import Empleado


class Command(BaseCommand):
    help = 'Crea el superusuario inicial desde variables de entorno si no existe ninguno'

    def handle(self, *args, **options):
        if Empleado.objects.filter(is_superuser=True).exists():
            self.stdout.write('Superusuario ya existe, omitiendo.')
            return

        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        if not password:
            self.stdout.write('DJANGO_SUPERUSER_PASSWORD no definida, omitiendo.')
            return

        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        carnet = os.environ.get('DJANGO_SUPERUSER_CARNET', '00000000')
        nombre = os.environ.get('DJANGO_SUPERUSER_NOMBRE', 'Administrador')

        Empleado.objects.create_superuser(
            username=username,
            password=password,
            carnet_identidad=carnet,
            nombre=nombre,
            cargo='administrador',
        )
        self.stdout.write(f'Superusuario "{username}" creado exitosamente.')
