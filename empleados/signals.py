from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AsignacionDiaria, ContratoEmpleado, JornadaEmpleado


def _crear_jornada_para(empleado, asignacion):
    """Crea una JornadaEmpleado para el empleado dado si tiene contrato activo."""
    if empleado is None:
        return
    contrato = ContratoEmpleado.objects.filter(
        empleado=empleado, activo=True
    ).first()
    if contrato is None:
        return
    # Evitar duplicado si ya existe jornada de esta asignación para este empleado
    ya_existe = JornadaEmpleado.objects.filter(
        contrato=contrato,
        proyecto=asignacion.proyecto,
        fecha=asignacion.fecha,
        asignacion=asignacion,
        activo=True,
    ).exists()
    if ya_existe:
        return
    # Validar que no supere 1.0 día total en esa fecha
    dias_ya = JornadaEmpleado.objects.filter(
        contrato=contrato, fecha=asignacion.fecha, activo=True
    ).exclude(asignacion=asignacion).aggregate(
        t=__import__('django.db.models', fromlist=['Sum']).Sum('dias')
    )['t'] or Decimal('0')

    dias_nuevos = asignacion.dias
    if dias_ya + dias_nuevos > Decimal('1.0'):
        return  # No se puede agregar más de 1 día; admin deberá ajustar manualmente

    JornadaEmpleado.objects.create(
        contrato=contrato,
        proyecto=asignacion.proyecto,
        fecha=asignacion.fecha,
        dias=dias_nuevos,
        observacion=asignacion.observacion,
        asignacion=asignacion,
    )


@receiver(post_save, sender=AsignacionDiaria)
def crear_jornadas_desde_asignacion(sender, instance, created, **kwargs):
    """Al crear una AsignacionDiaria, auto-genera JornadaEmpleado para cada miembro."""
    if not created:
        return
    _crear_jornada_para(instance.supervisor, instance)
    _crear_jornada_para(instance.instalador, instance)
