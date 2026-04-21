# Signals for projects app (Proyecto pre_save is in models.py)
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Sede, TareaChecklist, SubtareaChecklist


@receiver(post_save, sender=Sede)
def crear_tareas_desde_plantilla(sender, instance, created, **kwargs):
    """Al crear una sede con plantilla, copia los items (y sus sub-ítems) como TareaChecklist/SubtareaChecklist."""
    if not created or not instance.plantilla_id:
        return
    items = instance.plantilla.items.prefetch_related('subitems').order_by('orden')
    for item in items:
        tarea = TareaChecklist.objects.create(
            sede=instance,
            descripcion=item.descripcion,
            orden=item.orden,
        )
        for subitem in item.subitems.order_by('orden'):
            SubtareaChecklist.objects.create(
                tarea=tarea,
                descripcion=subitem.descripcion,
                orden=subitem.orden,
            )
