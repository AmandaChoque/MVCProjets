def user_cargo_context(request):
    """
    Inyecta el cargo del usuario y variables booleanas de rol en todos los templates.

    Variables disponibles en cualquier template:
        {{ user_cargo }}          — string con el cargo ('administrador', 'gerente', etc.) o None
        {% if es_admin %}         — solo administrador
        {% if es_admin_o_gerente %}  — administrador o gerente
        {% if es_admin_sec %}     — administrador, gerente o secretaria
        {% if es_campo %}         — administrador, gerente, instalador o tecnico_soporte
    """
    if not request.user.is_authenticated:
        return {}

    if request.user.is_superuser:
        cargo = 'administrador'
    else:
        try:
            cargo = request.user.employee_profile.cargo
        except AttributeError:
            cargo = None

    return {
        'user_cargo': cargo,
        'es_admin':               cargo == 'administrador',
        'es_admin_o_gerente':     cargo in ('administrador', 'gerente'),
        'es_admin_sec':           cargo in ('administrador', 'gerente', 'secretaria'),
        'es_campo':               cargo in ('administrador', 'gerente', 'instalador', 'tecnico_soporte'),
        'es_instalador_tecnico':  cargo in ('instalador', 'tecnico_soporte'),
    }
