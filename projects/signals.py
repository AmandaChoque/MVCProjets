# Signals for projects app (Proyecto pre_save is in models.py)
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Sede, TareaChecklist


@receiver(post_save, sender=Sede)
def crear_tareas_desde_plantilla(sender, instance, created, **kwargs):
    """Al crear una sede con plantilla, copia los items como TareaChecklist."""
    if not created or not instance.plantilla_id:
        return
    items = instance.plantilla.items.filter(activo=True).order_by('orden')
    for item in items:
        TareaChecklist.objects.create(
            sede=instance,
            descripcion=item.descripcion,
            orden=item.orden,
        )
