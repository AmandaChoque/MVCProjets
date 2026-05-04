def user_cargo_context(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.is_superuser:
        cargo = 'administrador'
    else:
        cargo = getattr(request.user, 'cargo', None)

    return {
        'user_cargo':            cargo,
        'es_admin':              cargo == 'administrador',
        'es_admin_o_gerente':    cargo in ('administrador', 'gerente'),
        'es_admin_sec':          cargo in ('administrador', 'gerente', 'secretaria'),
        'es_campo':              cargo in ('administrador', 'gerente', 'instalador', 'tecnico_soporte'),
        'es_instalador_tecnico': cargo in ('instalador', 'tecnico_soporte'),
    }
