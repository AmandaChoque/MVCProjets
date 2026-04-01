from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q, Count, Sum, OuterRef, Subquery
from django.utils import timezone
from django.template.loader import get_template
from django.core.paginator import Paginator
from xhtml2pdf import pisa

from .models import Empleado, PagoEmpleado, ContratoEmpleado, ContratoProyecto, JornadaEmpleado
from .forms import EmpleadoForm, ContratoEmpleadoForm, ContratoEmpleadoDesdeEmpleadoForm, JornadaEmpleadoForm, PagoEmpleadoForm
from projects.models import Proyecto, TareaChecklist
from projects.decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC


# ── Empleados ─────────────────────────────────────────────────────────────────

@login_required
@cargo_required('administrador')
def create_employee(request):
    if request.method == 'GET':
        return render(request, 'create_employee.html', {'form': EmpleadoForm()})
    form = EmpleadoForm(request.POST)
    if form.is_valid():
        employee = form.save(commit=False)
        employee.username = form.cleaned_data['username']
        employee.email = form.cleaned_data.get('correo') or ''
        employee.set_password(form.cleaned_data['password1'])
        employee.save()
        messages.success(request, f"El empleado {employee.nombre} {employee.apellido_paterno} fue registrado con acceso al sistema.")
        return redirect('employees')
    return render(request, 'create_employee.html', {'form': form, 'error': 'Por favor, proporcione datos válidos'})


@login_required
@cargo_required('administrador')
def deactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee, is_active=True)
    if request.method == 'POST':
        empleado.is_active = False
        empleado.save()
        messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue inhabilitado.")
    return redirect('employees')


@login_required
def employee_view(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)

    contratos = empleado.contratos_empleado.filter(activo=True).order_by('-created')
    contratos_con_pagos = []
    total_ganado_global = 0
    total_pagado_global = 0

    for contrato in contratos:
        pagos        = contrato.pagos.filter(activo=True).order_by('fecha')
        total_pagado = pagos.aggregate(t=Sum('monto'))['t'] or 0
        jornadas     = contrato.jornadas.filter(activo=True)
        total_dias   = jornadas.aggregate(t=Sum('dias'))['t'] or 0
        total_ganado = total_dias * contrato.monto_diario
        total_ganado_global += total_ganado
        total_pagado_global += total_pagado
        contratos_con_pagos.append({
            'contrato':       contrato,
            'pagos':          pagos,
            'total_dias':     total_dias,
            'total_ganado':   total_ganado,
            'total_pagado':   total_pagado,
            'saldo_jornadas': total_ganado - total_pagado,
        })

    saldo_global = total_ganado_global - total_pagado_global
    context = {
        'employee': empleado,
        'contratos_con_pagos': contratos_con_pagos,
        'total_ganado_global': total_ganado_global,
        'total_pagado_global': total_pagado_global,
        'saldo_global': saldo_global,
        'now': timezone.now(),
        'generado_por': request.user.get_full_name() or request.user.username,
    }

    if 'pdf' in request.GET:
        template = get_template('employee_detail_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        filename = f"ficha_empleado_{empleado.carnet_identidad}.pdf"
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    return render(request, 'employee_view.html', context)


@login_required
@cargo_required(*ROLES_ADMIN)
def employee_workload(request):
    empleados = Empleado.objects.filter(is_active=True).annotate(
        monto_contratos=Sum(
            'contratos_empleado__monto_acordado',
            filter=Q(contratos_empleado__activo=True)
        ),
    ).order_by('nombre')

    empleados_list = list(empleados)
    for emp in empleados_list:
        proyectos_activos_qs = emp.proyectos_asignados.filter(
            activo=True,
            estado_proyecto__in=['pendiente', 'en_progreso'],
        )
        proyectos_completados_count = emp.proyectos_asignados.filter(
            activo=True,
            estado_proyecto='completado',
        ).count()

        ids_activos = list(proyectos_activos_qs.values_list('id', flat=True))
        contratos_proyecto_map = {
            cp.proyecto_id: cp
            for cp in ContratoProyecto.objects.filter(proyecto_id__in=ids_activos, activo=True)
        }
        dias_por_proyecto = {
            row['proyecto_id']: row['total']
            for row in JornadaEmpleado.objects.filter(
                contrato__empleado=emp, activo=True,
                proyecto_id__in=ids_activos,
            ).values('proyecto_id').annotate(total=Sum('dias'))
        }
        emp.proyectos_activos = len(ids_activos)
        emp.proyectos_completados = proyectos_completados_count
        emp.total_dias = sum(dias_por_proyecto.values())
        emp.contratos_activos_list = [
            {
                'proyecto': p,
                'contrato_proyecto': contratos_proyecto_map.get(p.id),
                'dias_trabajados': dias_por_proyecto.get(p.id, 0),
            }
            for p in proyectos_activos_qs
        ]

    empleados_list.sort(key=lambda e: e.proyectos_activos, reverse=True)
    max_proyectos = max((e.proyectos_activos for e in empleados_list), default=1) or 1
    total_con_proyectos = sum(1 for e in empleados_list if e.proyectos_activos > 0)
    return render(request, 'employee_workload.html', {
        'empleados': empleados_list,
        'max_proyectos': max_proyectos,
        'total_con_proyectos': total_con_proyectos,
    })


@login_required
@cargo_required('administrador')
def employee_detail(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)
    if request.method == 'GET':
        form = EmpleadoForm(instance=empleado, initial={'correo': empleado.email})
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})
    form = EmpleadoForm(request.POST, instance=empleado)
    if form.is_valid():
        empleado = form.save()
        apellido_materno = form.cleaned_data.get('apellido_materno') or ''
        empleado.first_name = form.cleaned_data['nombre']
        empleado.last_name = f"{form.cleaned_data['apellido_paterno']} {apellido_materno}".strip()
        empleado.email = form.cleaned_data.get('correo') or ''
        nueva_password = form.cleaned_data.get('password1')
        if nueva_password:
            empleado.set_password(nueva_password)
            update_session_auth_hash(request, empleado)
        empleado.save(update_fields=['first_name', 'last_name', 'email', 'password'])
        messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue actualizado exitosamente.")
        return redirect('employees')
    return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})


@login_required
@cargo_required(*ROLES_ADMIN)
def employees(request):
    search_nombre = request.GET.get('search_nombre', '')
    filter_cargo  = request.GET.get('filter_cargo', '')
    page     = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        page = max(1, int(page))
    except ValueError:
        page = 1
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 10
    except ValueError:
        per_page = 10

    ultimo_proyecto = (
        JornadaEmpleado.objects
        .filter(contrato__empleado=OuterRef('pk'), activo=True)
        .order_by('-fecha')
        .values('proyecto__nombre')[:1]
    )
    empleados_qs = (
        Empleado.objects.filter(is_active=True)
        .annotate(proyecto_actual=Subquery(ultimo_proyecto))
        .order_by('-id')
    )
    if search_nombre:
        empleados_qs = empleados_qs.filter(
            Q(nombre__icontains=search_nombre) |
            Q(apellido_paterno__icontains=search_nombre) |
            Q(apellido_materno__icontains=search_nombre)
        )
    if filter_cargo:
        empleados_qs = empleados_qs.filter(cargo=filter_cargo)

    paginator = Paginator(empleados_qs, per_page)
    employees_page = paginator.get_page(page)
    return render(request, 'employees.html', {
        'employees': employees_page,
        'search_nombre': search_nombre,
        'filter_cargo': filter_cargo,
        'per_page': per_page,
    })


# ── Contratos de empleado ─────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN)
def create_contrato_from_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee, is_active=True)
    if request.method == 'GET':
        form = ContratoEmpleadoDesdeEmpleadoForm(empleado=empleado)
    else:
        form = ContratoEmpleadoDesdeEmpleadoForm(request.POST, request.FILES, empleado=empleado)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.empleado = empleado
            contrato.save()
            messages.success(request, f'Contrato registrado para {empleado.nombre} {empleado.apellido_paterno}.')
            return redirect('employee_view', id_employee=empleado.id)
    return render(request, 'create_contrato_desde_empleado.html', {'form': form, 'employee': empleado})


@login_required
@cargo_required(*ROLES_ADMIN)
def contrato_empleado_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.aggregate(t=Sum('dias'))['t'] or 0
    total_ganado    = total_dias * contrato.monto_diario
    pagos           = contrato.pagos.filter(activo=True).order_by('-fecha')
    total_pagado    = pagos.aggregate(t=Sum('monto'))['t'] or 0
    saldo_pendiente = total_ganado - total_pagado

    if request.method == 'GET':
        form = ContratoEmpleadoForm(instance=contrato)
    else:
        form = ContratoEmpleadoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contrato actualizado correctamente.')
            return redirect('employee_view', id_employee=contrato.empleado.id)

    return render(request, 'contrato_empleado_detail.html', {
        'form': form, 'contrato': contrato,
        'jornadas': jornadas, 'pagos': pagos,
        'total_dias': total_dias, 'total_ganado': total_ganado,
        'total_pagado': total_pagado, 'saldo_pendiente': saldo_pendiente,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_contrato_empleado(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)
    if request.method == 'POST':
        contrato.activo = False
        contrato.deleted_at = timezone.now()
        contrato.deleted_by = request.user
        contrato.save()
        messages.success(request, f'Contrato de {contrato.empleado.nombre} {contrato.empleado.apellido_paterno} inhabilitado.')
    return redirect('employee_view', id_employee=contrato.empleado.id)


# ── Jornadas ──────────────────────────────────────────────────────────────────

@login_required
def create_jornada(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)
    cargo = getattr(request.user, 'cargo', None)
    if cargo not in ROLES_ADMIN and contrato.empleado != request.user:
        messages.error(request, 'Solo puedes registrar jornadas en tu propio contrato.')
        return redirect('dashboard')
    es_admin = cargo in ROLES_ADMIN

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.aggregate(t=Sum('dias'))['t'] or 0
    total_ganado    = total_dias * contrato.monto_diario
    total_pagado    = contrato.pagos.filter(activo=True).aggregate(t=Sum('monto'))['t'] or 0
    saldo_pendiente = total_ganado - total_pagado

    if request.method == 'GET':
        form = JornadaEmpleadoForm(empleado=contrato.empleado, es_admin=es_admin, contrato=contrato)
    else:
        form = JornadaEmpleadoForm(request.POST, empleado=contrato.empleado, es_admin=es_admin, contrato=contrato)
        if form.is_valid():
            jornada = form.save(commit=False)
            jornada.contrato = contrato
            jornada.dias = form.cleaned_data['dias']
            jornada.save()
            messages.success(request, 'Jornada registrada correctamente.')
            return redirect('contrato_empleado_detail', id_contrato=contrato.id)

    return render(request, 'create_jornada.html', {
        'form': form, 'contrato': contrato,
        'jornadas': jornadas, 'total_dias': total_dias,
        'total_ganado': total_ganado, 'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def jornada_detail(request, id_jornada):
    jornada  = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    contrato = jornada.contrato
    if request.method == 'GET':
        form = JornadaEmpleadoForm(instance=jornada, es_admin=True, contrato=contrato)
    else:
        form = JornadaEmpleadoForm(request.POST, instance=jornada, es_admin=True, contrato=contrato)
        if form.is_valid():
            j = form.save(commit=False)
            j.dias = form.cleaned_data['dias']
            j.save()
            messages.success(request, 'Jornada actualizada correctamente.')
            return redirect('contrato_empleado_detail', id_contrato=contrato.id)
    return render(request, 'jornada_detail.html', {'form': form, 'jornada': jornada, 'contrato': contrato})


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    id_contrato = jornada.contrato.id
    if request.method == 'POST':
        jornada.activo = False
        jornada.deleted_at = timezone.now()
        jornada.deleted_by = request.user
        jornada.save()
        messages.success(request, 'Jornada eliminada.')
    return redirect('contrato_empleado_detail', id_contrato=id_contrato)


# ── Dashboard instalador ──────────────────────────────────────────────────────

@login_required
@cargo_required('instalador', 'tecnico_soporte', 'administrador', 'gerente')
def instalador_dashboard(request):
    user  = request.user
    cargo = getattr(user, 'cargo', None)

    if cargo in ('administrador', 'gerente'):
        proyectos = Proyecto.objects.filter(
            activo=True, estado_proyecto__in=['pendiente', 'en_progreso']
        ).prefetch_related('sedes').order_by('-created')
    else:
        proyectos = Proyecto.objects.filter(
            activo=True, estado_proyecto__in=['pendiente', 'en_progreso'], equipo=user,
        ).prefetch_related('sedes').order_by('-created')

    proyectos_data = []
    for p in proyectos:
        sedes       = p.sedes.filter(activo=True)
        total_tareas = TareaChecklist.objects.filter(sede__in=sedes, activo=True).count()
        tareas_ok    = TareaChecklist.objects.filter(sede__in=sedes, activo=True, completado=True).count()
        proyectos_data.append({
            'proyecto': p, 'sedes': sedes,
            'total_tareas': total_tareas, 'tareas_ok': tareas_ok,
            'pct_global': round(tareas_ok / total_tareas * 100) if total_tareas else 0,
        })

    mis_tareas_pendientes = TareaChecklist.objects.filter(
        activo=True, completado=False,
        sede__proyecto__equipo=user, sede__activo=True,
        sede__proyecto__estado_proyecto__in=['pendiente', 'en_progreso'],
    ).select_related('sede', 'sede__proyecto').order_by('sede__proyecto', 'sede', 'orden')

    return render(request, 'instalador_dashboard.html', {
        'proyectos_data': proyectos_data,
        'mis_tareas_pendientes': mis_tareas_pendientes,
        'no_leidas': user.notificaciones.filter(leida=False).count(),
    })


# ── Pagos a empleados ─────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def pagos_empleados_list(request):
    search_empleado = request.GET.get('search_empleado', '')
    search_proyecto = request.GET.get('search_proyecto', '')
    page     = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 10
    except ValueError:
        per_page = 10

    qs = PagoEmpleado.objects.filter(activo=True).select_related(
        'contrato__empleado'
    ).order_by('-fecha')
    if search_empleado:
        qs = qs.filter(
            Q(contrato__empleado__nombre__icontains=search_empleado) |
            Q(contrato__empleado__apellido_paterno__icontains=search_empleado)
        )
    if search_proyecto:
        qs = qs.filter(contrato__jornadas__proyecto__nombre__icontains=search_proyecto).distinct()

    paginator = Paginator(qs, per_page)
    pagos_page = paginator.get_page(page)

    total_monto = qs.aggregate(t=Sum('monto'))['t'] or 0
    contratos_activos = ContratoEmpleado.objects.filter(activo=True).select_related('empleado').order_by('empleado__nombre')

    return render(request, 'pagos_empleados_list.html', {
        'pagos': pagos_page,
        'search_empleado': search_empleado,
        'search_proyecto': search_proyecto,
        'contratos_activos': contratos_activos,
        'per_page': per_page,
        'total_monto': total_monto,
    })


def _contrato_resumen(contrato, excluir_pago_id=None):
    qs = PagoEmpleado.objects.filter(contrato=contrato, activo=True)
    if excluir_pago_id:
        qs = qs.exclude(pk=excluir_pago_id)
    pagado      = qs.aggregate(t=Sum('monto'))['t'] or 0
    total_dias  = contrato.jornadas.filter(activo=True).aggregate(t=Sum('dias'))['t'] or 0
    ganado      = total_dias * contrato.monto_diario
    return {
        'pagado':     pagado,
        'ganado':     ganado,
        'total_dias': total_dias,
        'saldo':      ganado - pagado,
    }


@login_required
@cargo_required(*ROLES_ADMIN)
def create_pago_empleado(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)
    resumen  = _contrato_resumen(contrato)
    jornadas_pendientes = JornadaEmpleado.objects.filter(
        contrato=contrato, activo=True, pago__isnull=True
    ).select_related('proyecto').order_by('fecha')

    if request.method == 'GET':
        return render(request, 'create_pago_empleado.html', {
            'form': PagoEmpleadoForm(),
            'contrato': contrato,
            'resumen': resumen,
            'jornadas_pendientes': jornadas_pendientes,
        })
    form = PagoEmpleadoForm(request.POST)
    if form.is_valid():
        pago = form.save(commit=False)
        pago.contrato = contrato
        pago.save()
        ids_seleccionados = request.POST.getlist('jornadas')
        if ids_seleccionados:
            JornadaEmpleado.objects.filter(
                pk__in=ids_seleccionados,
                contrato=contrato,
                activo=True,
                pago__isnull=True,
            ).update(pago=pago)
        messages.success(request, f'Pago de Bs. {pago.monto} registrado para {contrato.empleado.nombre}.')
        return redirect('employee_view', id_employee=contrato.empleado.id)
    return render(request, 'create_pago_empleado.html', {
        'form': form, 'contrato': contrato, 'resumen': resumen,
        'jornadas_pendientes': jornadas_pendientes,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def pago_empleado_detail(request, id_pago):
    pago     = get_object_or_404(PagoEmpleado, pk=id_pago, activo=True)
    contrato = pago.contrato
    resumen  = _contrato_resumen(contrato, excluir_pago_id=pago.id)
    jornadas_cubiertas  = pago.jornadas_cubiertas.filter(activo=True).select_related('proyecto').order_by('fecha')
    jornadas_pendientes = JornadaEmpleado.objects.filter(
        contrato=contrato, activo=True, pago__isnull=True
    ).select_related('proyecto').order_by('fecha')

    if request.method == 'GET':
        return render(request, 'pago_empleado_detail.html', {
            'form': PagoEmpleadoForm(instance=pago),
            'pago': pago,
            'contrato': contrato,
            'resumen': resumen,
            'jornadas_cubiertas': jornadas_cubiertas,
            'jornadas_pendientes': jornadas_pendientes,
        })
    form = PagoEmpleadoForm(request.POST, instance=pago)
    if form.is_valid():
        form.save()
        pago.jornadas_cubiertas.filter(activo=True).update(pago=None)
        ids_seleccionados = request.POST.getlist('jornadas')
        if ids_seleccionados:
            JornadaEmpleado.objects.filter(
                pk__in=ids_seleccionados,
                contrato=contrato,
                activo=True,
            ).update(pago=pago)
        messages.success(request, 'Pago actualizado correctamente.')
        return redirect('employee_view', id_employee=contrato.empleado.id)
    return render(request, 'pago_empleado_detail.html', {
        'form': form, 'pago': pago, 'contrato': contrato, 'resumen': resumen,
        'jornadas_cubiertas': jornadas_cubiertas,
        'jornadas_pendientes': jornadas_pendientes,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_pago_empleado(request, id_pago):
    pago     = get_object_or_404(PagoEmpleado, pk=id_pago)
    contrato = pago.contrato
    if request.method == 'POST':
        pago.jornadas_cubiertas.filter(activo=True).update(pago=None)
        pago.activo    = False
        pago.deleted_at = timezone.now()
        pago.deleted_by = request.user
        pago.save()
        messages.success(request, 'Pago eliminado correctamente.')
    return redirect('employee_view', id_employee=contrato.empleado.id)
