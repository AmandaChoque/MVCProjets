from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def dias_label(value):
    """Convierte valor decimal de dias a texto legible: 0.5 → '½ día', 1.0 → '1 día', 2.5 → '2½ días'."""
    try:
        val = float(value)
    except (TypeError, ValueError):
        return value
    if val == 0:
        return '0 días'
    entero = int(val)
    tiene_medio = (val - entero) >= 0.4
    if entero == 0 and tiene_medio:
        return '½ día'
    if tiene_medio:
        texto = f'{entero}½'
    else:
        texto = str(entero)
    return f'{texto} día' if val == 1.0 else f'{texto} días'
