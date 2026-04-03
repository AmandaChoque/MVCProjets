from django.apps import AppConfig


class EmpleadosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empleados'
    verbose_name = 'Gestión de Empleados'

    def ready(self):
        import empleados.signals  # noqa: F401
