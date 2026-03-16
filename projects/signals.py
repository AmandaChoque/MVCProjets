from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Realizar, Requiere


# ── Compras (Realizar) ──────────────────────────────────────────────────────

@receiver(post_save, sender=Realizar)
def realizar_post_save(sender, instance, **kwargs):
    instance.insumo.recalculate_stock()


@receiver(post_delete, sender=Realizar)
def realizar_post_delete(sender, instance, **kwargs):
    instance.insumo.recalculate_stock()


# ── Asignación a proyectos (Requiere) ────────────────────────────────────────

@receiver(post_save, sender=Requiere)
def requiere_post_save(sender, instance, **kwargs):
    instance.insumo.recalculate_stock()


@receiver(post_delete, sender=Requiere)
def requiere_post_delete(sender, instance, **kwargs):
    instance.insumo.recalculate_stock()
