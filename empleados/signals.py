from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import JornadaEmpleado


@receiver(post_save, sender=JornadaEmpleado)
def set_proyecto_fecha_inicio_en_primera_jornada(sender, instance, created, **kwargs):
    """
    Al registrar la primera jornada de un proyecto, fija fecha_inicio del proyecto
    si todavía está vacío. Usa update con fecha_inicio__isnull=True para que sea
    atómico y no sobreescriba fechas ya ingresadas.
    """
    if not created or not instance.activo:
        return
    proyecto = instance.proyecto
    if not proyecto or proyecto.fecha_inicio:
        return

    from projects.models import Proyecto
    Proyecto.objects.filter(pk=proyecto.pk, fecha_inicio__isnull=True).update(
        fecha_inicio=timezone.localdate()
    )
