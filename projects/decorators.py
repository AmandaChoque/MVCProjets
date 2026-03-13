from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# Grupos de roles reutilizables
ROLES_ADMIN     = ('administrador', 'gerente')
ROLES_ADMIN_SEC = ('administrador', 'gerente', 'secretaria')
ROLES_CAMPO     = ('administrador', 'gerente', 'instalador', 'tecnico_soporte')


def cargo_required(*cargos):
    """
    Restringe el acceso a una vista según el cargo del Empleado vinculado al usuario.

    Uso:
        @login_required
        @cargo_required('administrador')
        def mi_vista(request): ...

        @login_required
        @cargo_required(*ROLES_ADMIN)
        def otra_vista(request): ...

    Reglas:
    - Superusuarios de Django siempre tienen acceso.
    - Si el usuario no tiene perfil Empleado vinculado, se le deniega el acceso.
    - Si el cargo no está en la lista permitida, redirige al dashboard con un mensaje de error.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                cargo = request.user.employee_profile.cargo
            except AttributeError:
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect('dashboard')
            if cargo not in cargos:
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
