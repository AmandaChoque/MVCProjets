import calendar
from datetime import timedelta, date
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q, Count, Sum, OuterRef, Subquery, Exists
from django.utils import timezone
from django.template.loader import get_template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import Empleado, PagoEmpleado, ContratoEmpleado, JornadaEmpleado, METODOS_PAGO
from .forms import EmpleadoForm, ContratoEmpleadoForm, ContratoEmpleadoDesdeEmpleadoForm, JornadaEmpleadoForm, PagoEmpleadoForm
from projects.models import Proyecto, TareaChecklist, ContratoProyecto, Notificacion
from projects.decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC, ROLES_CAMPO


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
        messages.success(request, f"Empleado {employee.nombre} {employee.apellido_paterno} registrado. Ahora registra su contrato para que pueda registrar jornadas.")
        return redirect('create_contrato_from_employee', id_employee=employee.id)
    return render(request, 'create_employee.html', {'form': form, 'error': 'Por favor, proporcione datos válidos'})


@login_required
@cargo_required('administrador')
def deactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee, is_active=True)
    if request.method == 'POST':
        empleado.activo = False
        empleado.deleted_at = timezone.now()
        empleado.deleted_by = request.user
        empleado.save()
        messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue inhabilitado.")
    return redirect('employees')


@login_required
def employee_view(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)

    contratos = empleado.contratos_empleado.order_by('-created')
    contratos_con_pagos = []
    total_ganado_global = 0
    total_pagado_global = 0

    for contrato in contratos:
        pagos             = contrato.pagos.filter(activo=True, estado='pagado').order_by('fecha')
        total_pagado      = pagos.aggregate(t=Sum('monto'))['t'] or 0
        jornadas          = contrato.jornadas.filter(activo=True)
        total_dias        = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
        jornadas_pend     = jornadas.filter(estado='pendiente').count()
        total_ganado      = total_dias * contrato.monto_diario
        total_ganado_global += total_ganado
        total_pagado_global += total_pagado
        contratos_con_pagos.append({
            'contrato':           contrato,
            'pagos':              pagos,
            'total_dias':         total_dias,
            'total_ganado':       total_ganado,
            'total_pagado':       total_pagado,
            'saldo_jornadas':     total_ganado - total_pagado,
            'jornadas_pendientes': jornadas_pend,
        })

    context = {
        'employee': empleado,
        'contratos_con_pagos': contratos_con_pagos,
    }

    if 'pdf' in request.GET:
        saldo_global = total_ganado_global - total_pagado_global
        context.update({
            'total_ganado_global': total_ganado_global,
            'total_pagado_global': total_pagado_global,
            'saldo_global': saldo_global,
            'now': timezone.now(),
            'generado_por': request.user.get_full_name() or request.user.username,
        })
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
    filter_empleado = request.GET.get('filter_empleado', '')

    # ── Tab 1: jornadas pendientes (tabla plana, filtrable) ───────────────────
    jornadas_pend_qs = (
        JornadaEmpleado.objects.filter(activo=True, estado='pendiente')
        .select_related('contrato__empleado', 'proyecto')
        .order_by('contrato__empleado__apellido_paterno', 'fecha')
    )
    if filter_empleado:
        try:
            jornadas_pend_qs = jornadas_pend_qs.filter(contrato__empleado_id=int(filter_empleado))
        except ValueError:
            filter_empleado = ''

    # Empleados con jornadas pendientes (solo para la tabla)
    empleados_pendientes = (
        Empleado.objects.filter(
            contratos_empleado__jornadas__activo=True,
            contratos_empleado__jornadas__estado='pendiente',
        ).distinct().order_by('apellido_paterno', 'nombre')
    )

    # Todos los empleados activos (para el filtro del calendario)
    empleados_activos = (
        Empleado.objects.filter(is_active=True)
        .order_by('apellido_paterno', 'nombre')
    )

    # Contrato activo del empleado seleccionado (para indicadores en el calendario)
    contrato_cal = None
    if filter_empleado:
        try:
            contrato_cal = ContratoEmpleado.objects.filter(
                empleado_id=int(filter_empleado), activo=True,
            ).order_by('-created').first()
        except ValueError:
            pass

    # ── Calendario de jornadas ────────────────────────────────────────────────
    MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    DIAS_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    today = date.today()

    cal_vista = request.GET.get('cal_vista', 'mes')
    if cal_vista not in ('mes', 'semana', 'anio'):
        cal_vista = 'mes'

    fe = filter_empleado  # shorthand para URLs
    cal_weeks      = []
    cal_week_days  = []
    cal_anio_meses = []
    cal_mes_nombre = ''
    cal_nav_prev = cal_nav_next = cal_nav_hoy = '#'

    if cal_vista == 'mes':
        try:
            cal_mes  = int(request.GET.get('cal_mes',  today.month))
            cal_anio = int(request.GET.get('cal_anio', today.year))
            if not (1 <= cal_mes <= 12):
                cal_mes, cal_anio = today.month, today.year
        except ValueError:
            cal_mes, cal_anio = today.month, today.year

        cal_mes_nombre = f"{MESES_ES[cal_mes]} {cal_anio}"

        cal_jornadas_dict = {}
        cal_tareas_dict   = {}
        if fe:
            try:
                emp_id = int(fe)
                for j in JornadaEmpleado.objects.filter(
                    activo=True,
                    contrato__empleado_id=emp_id,
                    fecha__year=cal_anio,
                    fecha__month=cal_mes,
                ).select_related('proyecto'):
                    cal_jornadas_dict[j.fecha] = j
                for t in TareaChecklist.objects.filter(
                    activo=True,
                    completado=True,
                    participantes__id=emp_id,
                    fecha_completado__year=cal_anio,
                    fecha_completado__month=cal_mes,
                ).select_related('sede__proyecto').order_by('fecha_completado'):
                    d = t.fecha_completado.date()
                    cal_tareas_dict.setdefault(d, []).append(t)
            except ValueError:
                pass

        for week in calendar.monthcalendar(cal_anio, cal_mes):
            week_days = []
            for day_num in week:
                if day_num == 0:
                    week_days.append({'num': None, 'jornada': None, 'tareas': [], 'is_today': False, 'date': None})
                else:
                    d = date(cal_anio, cal_mes, day_num)
                    week_days.append({'num': day_num, 'date': d,
                                      'jornada': cal_jornadas_dict.get(d),
                                      'tareas':  cal_tareas_dict.get(d, []),
                                      'is_today': d == today})
            cal_weeks.append(week_days)

        p_mes  = 12 if cal_mes == 1 else cal_mes - 1
        p_anio = cal_anio - 1 if cal_mes == 1 else cal_anio
        n_mes  = 1 if cal_mes == 12 else cal_mes + 1
        n_anio = cal_anio + 1 if cal_mes == 12 else cal_anio
        base = f"?cal_vista=mes&filter_empleado={fe}"
        cal_nav_prev = f"{base}&cal_mes={p_mes}&cal_anio={p_anio}"
        cal_nav_next = f"{base}&cal_mes={n_mes}&cal_anio={n_anio}"
        cal_nav_hoy  = f"{base}&cal_mes={today.month}&cal_anio={today.year}"

    elif cal_vista == 'semana':
        try:
            cal_fecha = date.fromisoformat(request.GET.get('cal_fecha', today.isoformat()))
        except ValueError:
            cal_fecha = today

        week_start = cal_fecha - timedelta(days=cal_fecha.weekday())
        week_end   = week_start + timedelta(days=6)

        if week_start.month == week_end.month:
            cal_mes_nombre = f"{MESES_ES[week_start.month]} {week_start.year}"
        else:
            cal_mes_nombre = f"{MESES_ES[week_start.month]} – {MESES_ES[week_end.month]} {week_end.year}"

        cal_jornadas_dict = {}
        cal_tareas_dict   = {}
        if fe:
            try:
                emp_id = int(fe)
                for j in JornadaEmpleado.objects.filter(
                    activo=True,
                    contrato__empleado_id=emp_id,
                    fecha__range=[week_start, week_end],
                ).select_related('proyecto'):
                    cal_jornadas_dict[j.fecha] = j
                for t in TareaChecklist.objects.filter(
                    activo=True,
                    completado=True,
                    participantes__id=emp_id,
                    fecha_completado__date__range=[week_start, week_end],
                ).select_related('sede__proyecto').order_by('fecha_completado'):
                    d = t.fecha_completado.date()
                    cal_tareas_dict.setdefault(d, []).append(t)
            except ValueError:
                pass

        for i in range(7):
            d = week_start + timedelta(days=i)
            cal_week_days.append({
                'num': d.day, 'date': d, 'dia_nombre': DIAS_ES[i],
                'jornada': cal_jornadas_dict.get(d),
                'tareas':  cal_tareas_dict.get(d, []),
                'is_today': d == today,
            })

        base = f"?cal_vista=semana&filter_empleado={fe}"
        cal_nav_prev = f"{base}&cal_fecha={(week_start - timedelta(days=7)).isoformat()}"
        cal_nav_next = f"{base}&cal_fecha={(week_start + timedelta(days=7)).isoformat()}"
        cal_nav_hoy  = f"{base}&cal_fecha={today.isoformat()}"

    else:  # anio
        try:
            cal_anio_num = int(request.GET.get('cal_anio', today.year))
        except ValueError:
            cal_anio_num = today.year

        cal_mes_nombre = str(cal_anio_num)

        cal_jornadas_dict = {}
        cal_tareas_dict   = {}
        if fe:
            try:
                emp_id = int(fe)
                for j in JornadaEmpleado.objects.filter(
                    activo=True,
                    contrato__empleado_id=emp_id,
                    fecha__year=cal_anio_num,
                ).select_related('proyecto'):
                    cal_jornadas_dict[j.fecha] = j
                for t in TareaChecklist.objects.filter(
                    activo=True,
                    completado=True,
                    participantes__id=emp_id,
                    fecha_completado__year=cal_anio_num,
                ).select_related('sede__proyecto'):
                    d = t.fecha_completado.date()
                    cal_tareas_dict.setdefault(d, []).append(t)
            except ValueError:
                pass

        for mes in range(1, 13):
            weeks = []
            for week in calendar.monthcalendar(cal_anio_num, mes):
                week_days = []
                for day_num in week:
                    if day_num == 0:
                        week_days.append({'num': None, 'date': None, 'jornada': None, 'tareas': []})
                    else:
                        d = date(cal_anio_num, mes, day_num)
                        week_days.append({
                            'num':      day_num,
                            'date':     d,
                            'jornada':  cal_jornadas_dict.get(d),
                            'tareas':   cal_tareas_dict.get(d, []),
                            'is_today': d == today,
                        })
                weeks.append(week_days)
            cal_anio_meses.append({'mes': mes, 'nombre': MESES_ES[mes], 'weeks': weeks})

        base = f"?cal_vista=anio&filter_empleado={fe}"
        cal_nav_prev = f"{base}&cal_anio={cal_anio_num - 1}"
        cal_nav_next = f"{base}&cal_anio={cal_anio_num + 1}"
        cal_nav_hoy  = f"{base}&cal_anio={today.year}"

    return render(request, 'employee_workload.html', {
        'jornadas_pendientes':  list(jornadas_pend_qs),
        'empleados_pendientes': empleados_pendientes,
        'empleados_activos':    empleados_activos,
        'contrato_cal':         contrato_cal,
        'cal_anio_meses':       cal_anio_meses,
        'filter_empleado':      filter_empleado,
        'total_pendientes':     jornadas_pend_qs.count(),
        'cal_vista':              cal_vista,
        'cal_weeks':              cal_weeks,
        'cal_week_days':          cal_week_days,
        'cal_mes_nombre':         cal_mes_nombre,
        'cal_nav_prev':           cal_nav_prev,
        'cal_nav_next':           cal_nav_next,
        'cal_nav_hoy':            cal_nav_hoy,
        'today':                  today,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def aprobar_todas_jornadas(request):
    if request.method != 'POST':
        return redirect('employee_workload')
    empleado_id = request.POST.get('filter_empleado', '')
    qs = JornadaEmpleado.objects.filter(activo=True, estado='pendiente')
    if empleado_id:
        try:
            qs = qs.filter(contrato__empleado_id=int(empleado_id))
        except ValueError:
            pass
    qs = list(qs.select_related('contrato__empleado', 'proyecto'))

    # Solo aprobar jornadas con evidencia de tareas completadas ese día en el proyecto
    con_evidencia = []
    for j in qs:
        tiene_evidencia = TareaChecklist.objects.filter(
            sede__proyecto=j.proyecto,
            completado=True,
            fecha_completado__date=j.fecha,
            participantes=j.contrato.empleado,
            activo=True,
        ).exists()
        if tiene_evidencia:
            con_evidencia.append(j)

    # Agrupar por contrato para crear un pago por empleado (no uno por jornada)
    from collections import defaultdict
    por_contrato = defaultdict(list)
    for j in con_evidencia:
        por_contrato[j.contrato_id].append(j)

    count = 0
    hoy = timezone.localdate()
    notifs = []
    for contrato_id, jornadas in por_contrato.items():
        monto_total = sum(j.monto for j in jornadas)
        contrato = jornadas[0].contrato
        pago = PagoEmpleado.objects.create(
            contrato=contrato,
            monto=monto_total,
            fecha=hoy,
            tipo_pago='efectivo',
            concepto='pago_jornada',
            estado='pendiente',
        )
        for j in jornadas:
            j.estado = 'aprobada'
            j.motivo_rechazo = ''
            j.pago = pago
            j.save()
            notifs.append(Notificacion(
                destinatario=contrato.empleado,
                tipo='general',
                mensaje=(
                    f'Tu jornada del {j.fecha.strftime("%d/%m/%Y")} '
                    f'({j.dias} día(s)) en "{j.proyecto.nombre}" fue aprobada.'
                ),
                proyecto=j.proyecto,
            ))
            count += 1
    if notifs:
        Notificacion.objects.bulk_create(notifs)
    messages.success(request, f'{count} jornada{"s" if count != 1 else ""} aprobada{"s" if count != 1 else ""} con evidencia de tareas.')
    redirect_url = reverse('employee_workload')
    if empleado_id:
        redirect_url += f'?filter_empleado={empleado_id}'
    return redirect(redirect_url)


@login_required
@cargo_required('administrador')
def employee_detail(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)
    if request.method == 'GET':
        form = EmpleadoForm(instance=empleado, initial={'correo': empleado.email})
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})
    form = EmpleadoForm(request.POST, instance=empleado)
    if form.is_valid():
        empleado = form.save(commit=False)
        empleado.email = form.cleaned_data.get('correo') or ''
        nueva_password = form.cleaned_data.get('password1')
        if nueva_password:
            empleado.set_password(nueva_password)
            update_session_auth_hash(request, empleado)
        empleado.save()
        messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue actualizado exitosamente.")
        return redirect('employees')
    messages.error(request, 'Por favor corrija los errores del formulario.')
    return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})


@login_required
@cargo_required(*ROLES_ADMIN)
def employees(request):
    search_nombre = request.GET.get('search_nombre', '')
    filter_cargo  = request.GET.get('filter_cargo', '')
    filter_estado = request.GET.get('filter_estado', 'activo')
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
    contrato_activo = ContratoEmpleado.objects.filter(empleado=OuterRef('pk'), activo=True)
    empleados_qs = (
        Empleado.objects
        .annotate(
            proyecto_actual=Subquery(ultimo_proyecto),
            tiene_contrato=Exists(contrato_activo),
        )
        .order_by('-id')
    )

    if filter_estado == 'deshabilitado':
        empleados_qs = empleados_qs.filter(is_active=False)
    elif filter_estado == 'todos':
        pass
    else:
        empleados_qs = empleados_qs.filter(is_active=True)

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
        'filter_estado': filter_estado,
        'per_page': per_page,
    })


@login_required
@cargo_required('administrador')
def reactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee, is_active=False)
    if request.method == 'POST':
        empleado.is_active = True
        empleado.save()
        messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue habilitado nuevamente.")
    return redirect('employees')


# ── Reporte de empleados ──────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN)
def employee_report(request):
    search_nombre = request.GET.get('search_nombre', '').strip()
    filter_cargo  = request.GET.get('filter_cargo', '')
    per_page = int(request.GET.get('per_page', 10))
    if per_page not in (10, 20, 50, 100):
        per_page = 10
    page = request.GET.get('page', 1)

    empleados_qs = Empleado.objects.filter(is_active=True).prefetch_related(
        'contratos_empleado'
    ).order_by('apellido_paterno', 'nombre')

    if search_nombre:
        empleados_qs = empleados_qs.filter(
            Q(nombre__icontains=search_nombre) |
            Q(apellido_paterno__icontains=search_nombre) |
            Q(apellido_materno__icontains=search_nombre)
        )
    if filter_cargo:
        empleados_qs = empleados_qs.filter(cargo=filter_cargo)

    empleados_list = list(empleados_qs)

    # Enriquecer cada empleado con datos de contrato, jornadas y pagos
    for emp in empleados_list:
        contrato = emp.contratos_empleado.filter(activo=True).order_by('-created').first()
        emp.contrato_activo = contrato
        if contrato:
            jornadas_agg = contrato.jornadas.filter(activo=True).aggregate(t=Sum('dias'))
            total_dias   = jornadas_agg['t'] or 0
            total_ganado = total_dias * contrato.monto_diario
            total_pagado = contrato.pagos.filter(activo=True, estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
            emp.total_dias    = total_dias
            emp.total_ganado  = total_ganado
            emp.total_pagado  = total_pagado
            emp.saldo_pendiente = total_ganado - total_pagado
        else:
            emp.total_dias = emp.total_ganado = emp.total_pagado = emp.saldo_pendiente = 0

    # KPIs
    total_empleados = len(empleados_list)
    con_contrato    = sum(1 for e in empleados_list if e.contrato_activo)
    sin_contrato    = total_empleados - con_contrato
    cargo_counts    = {}
    for e in empleados_list:
        cargo_counts[e.cargo] = cargo_counts.get(e.cargo, 0) + 1

    tot_devengado = sum(emp.total_ganado  for emp in empleados_list)
    tot_saldo     = sum(emp.saldo_pendiente for emp in empleados_list)

    # PDF/Excel: lista completa; HTML: paginada
    if 'pdf' in request.GET or 'excel' in request.GET:
        empleados_page = None
    else:
        paginator = Paginator(empleados_list, per_page)
        try:
            empleados_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            empleados_page = paginator.page(1)
        empleados_list = list(empleados_page.object_list)

    context = {
        'empleados':      empleados_list,
        'search_nombre':  search_nombre,
        'filter_cargo':   filter_cargo,
        'cargo_choices':  Empleado.POSITION_CHOICES,
        'total_empleados': total_empleados,
        'con_contrato':   con_contrato,
        'sin_contrato':   sin_contrato,
        'cargo_counts':   cargo_counts,
        'tot_devengado':  tot_devengado,
        'tot_saldo':      tot_saldo,
        'empleados_page': empleados_page,
        'per_page':       per_page,
        'now':            timezone.now(),
        'generado_por':   request.user.get_full_name() or request.user.username,
    }

    if 'pdf' in request.GET:
        template = get_template('employee_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="reporte_empleados.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    if 'excel' in request.GET:
        NUM_COLS = 10
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Empleados'

        title_fill  = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        title_font  = Font(bold=True, size=14, color='D4B84A')
        info_fill   = PatternFill(start_color='1B4D90', end_color='1B4D90', fill_type='solid')
        info_font   = Font(size=9, color='FFFFFF')
        header_fill = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        header_font = Font(bold=True, color='D4B84A', size=10)
        alt_fill    = PatternFill(start_color='EFF2F8', end_color='EFF2F8', fill_type='solid')
        total_fill  = PatternFill(start_color='E8EDF5', end_color='E8EDF5', fill_type='solid')
        total_font  = Font(bold=True, size=10, color='0F2D5A')
        center      = Alignment(horizontal='center', vertical='center')
        left        = Alignment(horizontal='left',   vertical='center')
        right_al    = Alignment(horizontal='right',  vertical='center')
        cell_border = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='thin', color='C0C8D8'),  bottom=Side(style='thin', color='C0C8D8'),
        )
        total_border = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='medium', color='0F2D5A'), bottom=Side(style='medium', color='0F2D5A'),
        )
        money_fmt = '#,##0.00'

        ws.append(['Reporte de Empleados — SOBOTEC S.R.L.'])
        ws.merge_cells(f'A1:{openpyxl.utils.get_column_letter(NUM_COLS)}1')
        ws['A1'].font = title_font; ws['A1'].fill = title_fill
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 26

        info_str = f'Generado por: {context["generado_por"]}  |  Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        if search_nombre: info_str += f'  |  Nombre: {search_nombre}'
        if filter_cargo:  info_str += f'  |  Cargo: {filter_cargo}'
        ws.append([info_str])
        ws.merge_cells(f'A2:{openpyxl.utils.get_column_letter(NUM_COLS)}2')
        ws['A2'].font = info_font; ws['A2'].fill = info_fill
        ws['A2'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[2].height = 18

        ws.append([])
        ws.row_dimensions[3].height = 6

        headers = ['Nombre Completo', 'CI', 'Cargo', 'Celular',
                   'Modalidad Pago', 'Monto Acordado (Bs.)', 'Inicio Contrato', 'Fin Contrato',
                   'Total Devengado (Bs.)', 'Saldo Pendiente (Bs.)']
        ws.append(headers)
        for cell in ws[4]:
            cell.font = header_font; cell.fill = header_fill
            cell.alignment = center; cell.border = cell_border
        ws.row_dimensions[4].height = 22

        last_row = 4
        tot_devengado = tot_saldo = 0
        for i, emp in enumerate(empleados_list, start=5):
            c = emp.contrato_activo
            ws.append([
                f'{emp.nombre} {emp.apellido_paterno} {emp.apellido_materno or ""}'.strip(),
                emp.carnet_identidad,
                emp.get_cargo_display(),
                emp.numero_celular or '—',
                f'{c.dias_laborales} días' if c else '—',
                float(c.monto_acordado) if c else 0,
                c.fecha_inicio.strftime('%d/%m/%Y') if c else '—',
                c.fecha_fin.strftime('%d/%m/%Y') if c else '—',
                float(emp.total_ganado),
                float(emp.saldo_pendiente),
            ])
            row_fill = alt_fill if i % 2 == 0 else None
            for j, cell in enumerate(ws[i], start=1):
                if row_fill: cell.fill = row_fill
                cell.border = cell_border
                if j in (6, 9, 10):
                    cell.alignment = right_al; cell.number_format = money_fmt
                elif j in (7, 8):
                    cell.alignment = center
                else:
                    cell.alignment = left
            ws.row_dimensions[i].height = 16
            last_row = i
            tot_devengado += float(emp.total_ganado)
            tot_saldo     += float(emp.saldo_pendiente)

        total_row = last_row + 1
        ws.append(['', '', '', '', '', '', 'TOTAL', '', tot_devengado, tot_saldo])
        for j, cell in enumerate(ws[total_row], start=1):
            cell.font = total_font; cell.fill = total_fill; cell.border = total_border
            if j in (9, 10):
                cell.alignment = right_al; cell.number_format = money_fmt
            else:
                cell.alignment = left
        ws.row_dimensions[total_row].height = 18

        col_widths = [30, 14, 18, 14, 16, 20, 16, 16, 22, 22]
        for col_idx, width in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        ws.freeze_panes = 'A5'
        ws.auto_filter.ref = f'A4:{openpyxl.utils.get_column_letter(NUM_COLS)}4'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="reporte_empleados.xlsx"'
        wb.save(response)
        return response

    return render(request, 'employee_report.html', context)


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
            ContratoEmpleado.objects.filter(
                empleado=empleado, activo=True, fecha_fin__lt=date.today()
            ).update(activo=False)
            contrato = form.save(commit=False)
            contrato.empleado = empleado
            contrato.save()
            messages.success(request, f'Contrato registrado para {empleado.nombre} {empleado.apellido_paterno}.')
            return redirect('contrato_empleado_detail', id_contrato=contrato.id)
    return render(request, 'create_contrato_desde_empleado.html', {'form': form, 'employee': empleado})


@login_required
@cargo_required(*ROLES_ADMIN)
def contrato_empleado_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato)

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
    total_ganado    = total_dias * contrato.monto_diario
    pagos              = contrato.pagos.filter(activo=True).order_by('-fecha')
    total_pagado       = pagos.filter(estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
    total_por_confirmar = pagos.filter(estado='pendiente').aggregate(t=Sum('monto'))['t'] or 0
    saldo_pendiente    = total_ganado - total_pagado

    pct_dias = min(100, round(float(total_dias) / float(contrato.dias_laborales) * 100)) if contrato.dias_laborales else 0

    if request.method == 'GET':
        form = ContratoEmpleadoDesdeEmpleadoForm(instance=contrato, empleado=contrato.empleado)
    else:
        form = ContratoEmpleadoDesdeEmpleadoForm(request.POST, request.FILES, instance=contrato, empleado=contrato.empleado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contrato actualizado correctamente.')
            return redirect('employee_view', id_employee=contrato.empleado.id)

    return render(request, 'contrato_empleado_detail.html', {
        'form': form, 'contrato': contrato,
        'jornadas': jornadas, 'pagos': pagos,
        'total_dias': total_dias, 'total_ganado': total_ganado,
        'total_pagado': total_pagado, 'total_por_confirmar': total_por_confirmar,
        'saldo_pendiente': saldo_pendiente,
        'pct_dias': pct_dias,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def contrato_empleado_pdf(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato)
    gerente = Empleado.objects.filter(cargo='gerente').first()
    context = {
        'contrato': contrato,
        'gerente': gerente,
        'now': timezone.now(),
        'generado_por': request.user.get_full_name() or request.user.username,
    }
    template = get_template('contrato_empleado_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    nombre = f"{contrato.empleado.apellido_paterno}_{contrato.empleado.nombre}".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="contrato_{nombre}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    return response


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
@cargo_required(*ROLES_CAMPO)
def create_jornada(request, id_contrato):
    import json
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato)
    cargo = getattr(request.user, 'cargo', None)
    if cargo not in ROLES_ADMIN and contrato.empleado != request.user:
        messages.error(request, 'Solo puedes registrar jornadas en tu propio contrato.')
        return redirect('dashboard')
    es_admin = cargo in ROLES_ADMIN

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
    total_ganado    = total_dias * contrato.monto_diario
    total_pagado    = contrato.pagos.filter(activo=True, estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
    saldo_pendiente = total_ganado - total_pagado

    # Mapa proyecto_id → lista de compañeros para filtrado JS en el template
    base_qs = Proyecto.objects.filter(activo=True, estado_proyecto__in=['pendiente', 'en_progreso'])
    if not es_admin:
        proyectos_disponibles = base_qs.filter(equipo=contrato.empleado)
    else:
        proyectos_disponibles = base_qs
    companeros_por_proyecto = {}
    for p in proyectos_disponibles.prefetch_related('equipo'):
        companeros_por_proyecto[p.id] = [
            {'id': e.id, 'nombre': e.get_full_name(), 'cargo': e.get_cargo_display()}
            for e in p.equipo.filter(is_active=True).exclude(pk=contrato.empleado.pk)
        ]

    if request.method == 'GET':
        form = JornadaEmpleadoForm(
            empleado=contrato.empleado, es_admin=es_admin, contrato=contrato,
        )
    else:
        form = JornadaEmpleadoForm(
            request.POST, empleado=contrato.empleado, es_admin=es_admin, contrato=contrato,
        )
        if form.is_valid():
            # Guardar la jornada propia
            jornada = form.save(commit=False)
            jornada.contrato = contrato
            jornada.dias = form.cleaned_data['dias']
            jornada.registrado_por = request.user
            jornada.save()

            # Crear jornadas para los compañeros seleccionados
            companeros = form.cleaned_data.get('companeros', [])
            errores_companeros = []
            creadas_companeros = []
            for companero in companeros:
                contrato_comp = companero.contratos_empleado.filter(activo=True).order_by('-created').first()
                if not contrato_comp:
                    errores_companeros.append(f'{companero.get_full_name()} no tiene contrato activo.')
                    continue
                fecha = form.cleaned_data['fecha']
                if not (contrato_comp.fecha_inicio <= fecha <= contrato_comp.fecha_fin):
                    errores_companeros.append(
                        f'{companero.get_full_name()}: la fecha está fuera del rango de su contrato.'
                    )
                    continue
                ya_existe = JornadaEmpleado.objects.filter(
                    contrato=contrato_comp, proyecto=jornada.proyecto, fecha=fecha, activo=True,
                ).exists()
                if ya_existe:
                    errores_companeros.append(
                        f'{companero.get_full_name()} ya tiene jornada registrada ese día en este proyecto.'
                    )
                    continue
                JornadaEmpleado.objects.create(
                    contrato=contrato_comp,
                    proyecto=jornada.proyecto,
                    fecha=fecha,
                    dias=jornada.dias,
                    observacion=jornada.observacion,
                    registrado_por=request.user,
                )
                creadas_companeros.append(companero.get_full_name())

            if creadas_companeros:
                messages.success(request, f'Jornada registrada también para: {", ".join(creadas_companeros)}.')
            for err in errores_companeros:
                messages.warning(request, err)

            messages.success(request, 'Jornada registrada correctamente.')
            if not es_admin:
                return redirect('instalador_dashboard')
            return redirect('contrato_empleado_detail', id_contrato=contrato.id)

    hoy_cj = timezone.localdate()
    contrato_vencido = not contrato.activo or contrato.fecha_fin < hoy_cj
    return render(request, 'create_jornada.html', {
        'form': form, 'contrato': contrato,
        'jornadas': jornadas, 'total_dias': total_dias,
        'total_ganado': total_ganado, 'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'from_dashboard': not es_admin,
        'companeros_por_proyecto_json': json.dumps(companeros_por_proyecto),
        'contrato_vencido': contrato_vencido,
    })


@login_required
def jornada_detail(request, id_jornada):
    jornada  = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    contrato = jornada.contrato
    cargo    = getattr(request.user, 'cargo', None)
    es_admin = cargo in ROLES_ADMIN
    if not es_admin and contrato.empleado != request.user:
        messages.error(request, 'No tenés permiso para editar esta jornada.')
        return redirect('instalador_dashboard')
    # Instalador no puede editar una jornada ya aprobada
    if not es_admin and jornada.estado == 'aprobada':
        messages.error(request, 'Esta jornada ya fue aprobada y no puede modificarse.')
        return redirect('instalador_dashboard')
    if request.method == 'GET':
        form = JornadaEmpleadoForm(instance=jornada, es_admin=es_admin, contrato=contrato)
    else:
        form = JornadaEmpleadoForm(request.POST, instance=jornada, es_admin=es_admin, contrato=contrato)
        if form.is_valid():
            j = form.save(commit=False)
            j.dias = form.cleaned_data['dias']
            j.save()
            messages.success(request, 'Jornada actualizada correctamente.')
            if es_admin:
                return redirect('contrato_empleado_detail', id_contrato=contrato.id)
            return redirect('instalador_dashboard')
    # Todas las tareas completadas ese día en el proyecto (sin filtrar por empleado)
    tareas_del_dia = TareaChecklist.objects.filter(
        sede__proyecto=jornada.proyecto,
        completado=True,
        fecha_completado__date=jornada.fecha,
        activo=True,
    ).select_related('sede', 'completado_por').order_by('sede__nombre', 'orden')
    hoy_jd = timezone.localdate()
    contrato_vencido = not contrato.activo or contrato.fecha_fin < hoy_jd
    return render(request, 'jornada_detail.html', {
        'form': form, 'jornada': jornada, 'contrato': contrato,
        'tareas_del_dia': tareas_del_dia, 'es_admin': es_admin,
        'contrato_vencido': contrato_vencido,
    })


def _limpiar_pago_pendiente(jornada):
    """Si la jornada tiene un PagoEmpleado pendiente auto-creado, lo ajusta o desactiva."""
    if jornada.pago_id and jornada.pago.estado == 'pendiente':
        pago = jornada.pago
        otras = pago.jornadas_cubiertas.filter(activo=True).exclude(pk=jornada.pk).count()
        if otras == 0:
            pago.activo = False
        else:
            pago.monto = max(0, pago.monto - jornada.monto)
        pago.save()


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    id_contrato = jornada.contrato.id
    if request.method == 'POST':
        _limpiar_pago_pendiente(jornada)
        jornada.activo = False
        jornada.deleted_at = timezone.now()
        jornada.deleted_by = request.user
        jornada.save()
        messages.success(request, 'Jornada eliminada.')
    return redirect('contrato_empleado_detail', id_contrato=id_contrato)


@login_required
@cargo_required(*ROLES_ADMIN)
def aprobar_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    if request.method == 'POST':
        jornada.estado = 'aprobada'
        jornada.motivo_rechazo = ''

        pago_pendiente = PagoEmpleado.objects.filter(
            contrato=jornada.contrato,
            estado='pendiente',
            concepto='pago_jornada',
            activo=True,
        ).first()
        if pago_pendiente:
            pago_pendiente.monto += jornada.monto
            pago_pendiente.save()
        else:
            pago_pendiente = PagoEmpleado.objects.create(
                contrato=jornada.contrato,
                monto=jornada.monto,
                fecha=timezone.localdate(),
                tipo_pago='efectivo',
                concepto='pago_jornada',
                estado='pendiente',
            )
        jornada.pago = pago_pendiente
        jornada.save()

        Notificacion.objects.create(
            destinatario=jornada.contrato.empleado,
            tipo='general',
            mensaje=(
                f'Tu jornada del {jornada.fecha.strftime("%d/%m/%Y")} '
                f'({jornada.dias} día(s)) en "{jornada.proyecto.nombre}" fue aprobada.'
            ),
            proyecto=jornada.proyecto,
        )

        messages.success(request, 'Jornada aprobada.')
    next_url = request.POST.get('next', '')
    if next_url:
        return redirect(next_url)
    return redirect('revisar_jornadas_proyecto', id_proyecto=jornada.proyecto.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def rechazar_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    if request.method == 'POST':
        motivo = request.POST.get('motivo_rechazo', '').strip()
        _limpiar_pago_pendiente(jornada)
        jornada.estado = 'rechazada'
        jornada.motivo_rechazo = motivo
        jornada.pago = None
        jornada.save()
        motivo_txt = f' Motivo: {motivo}' if motivo else ''
        Notificacion.objects.create(
            destinatario=jornada.contrato.empleado,
            tipo='general',
            mensaje=(
                f'Tu jornada del {jornada.fecha.strftime("%d/%m/%Y")} '
                f'({jornada.dias} día(s)) en "{jornada.proyecto.nombre}" fue rechazada.{motivo_txt}'
            ),
            proyecto=jornada.proyecto,
        )
        messages.success(request, 'Jornada rechazada.')
    next_url = request.POST.get('next', '')
    if next_url:
        return redirect(next_url)
    return redirect('revisar_jornadas_proyecto', id_proyecto=jornada.proyecto.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def revisar_jornadas_proyecto(request, id_proyecto):
    from projects.models import Proyecto
    proyecto = get_object_or_404(Proyecto, pk=id_proyecto, activo=True)

    # Aprobación en lote: aprobar todas las pendientes con evidencia de tareas
    if request.method == 'POST' and request.POST.get('accion') == 'aprobar_con_evidencia':
        pendientes = list(
            JornadaEmpleado.objects.filter(
                activo=True, proyecto=proyecto, estado='pendiente',
            ).select_related('contrato__empleado')
        )

        # Filtrar solo las que tienen evidencia de tareas
        con_evidencia = []
        for j in pendientes:
            tiene_evidencia = TareaChecklist.objects.filter(
                sede__proyecto=proyecto,
                completado=True,
                fecha_completado__date=j.fecha,
                participantes=j.contrato.empleado,
                activo=True,
            ).exists()
            if tiene_evidencia:
                con_evidencia.append(j)

        # Agrupar por contrato para un pago por empleado
        from collections import defaultdict
        por_contrato = defaultdict(list)
        for j in con_evidencia:
            por_contrato[j.contrato_id].append(j)

        aprobadas = 0
        notifs = []
        hoy = timezone.localdate()
        for contrato_id, jornadas in por_contrato.items():
            monto_total = sum(j.monto for j in jornadas)
            contrato = jornadas[0].contrato
            pago = PagoEmpleado.objects.create(
                contrato=contrato,
                monto=monto_total,
                fecha=hoy,
                tipo_pago='efectivo',
                concepto='pago_jornada',
                estado='pendiente',
            )
            for j in jornadas:
                j.estado = 'aprobada'
                j.motivo_rechazo = ''
                j.pago = pago
                j.save()
                aprobadas += 1
                notifs.append(Notificacion(
                    destinatario=contrato.empleado,
                    tipo='general',
                    mensaje=(
                        f'Tu jornada del {j.fecha.strftime("%d/%m/%Y")} '
                        f'({j.dias} día(s)) en "{proyecto.nombre}" fue aprobada.'
                    ),
                    proyecto=proyecto,
                ))
        if notifs:
            Notificacion.objects.bulk_create(notifs)
        messages.success(request, f'{aprobadas} jornada(s) aprobada(s) automáticamente por evidencia de tareas.')
        return redirect('revisar_jornadas_proyecto', id_proyecto=id_proyecto)

    # Todos los empleados asignados al proyecto
    empleados = proyecto.equipo.filter(is_active=True).order_by('apellido_paterno', 'nombre')

    estado_filtro = request.GET.get('estado', 'pendiente')

    empleados_data = []
    total_pendientes_con_evidencia = 0
    for emp in empleados:
        # Contrato más reciente (activo o vencido) — solo para mostrar monto/día
        contrato = emp.contratos_empleado.order_by('-created').first()

        # Jornadas por empleado+proyecto directamente (no por contrato activo)
        todas_qs = JornadaEmpleado.objects.filter(
            activo=True, proyecto=proyecto, contrato__empleado=emp,
        )
        qs = todas_qs
        if estado_filtro in ('pendiente', 'aprobada', 'rechazada'):
            qs = qs.filter(estado=estado_filtro)
        jornadas = list(qs.select_related('contrato', 'registrado_por').order_by('-fecha'))

        # Anotar cada jornada con las tareas completadas ese día y si el contrato está vencido
        hoy = timezone.localdate()
        for j in jornadas:
            j.tareas_del_dia = list(TareaChecklist.objects.filter(
                sede__proyecto=proyecto,
                completado=True,
                fecha_completado__date=j.fecha,
                participantes=emp,
                activo=True,
            ).select_related('sede').order_by('sede__nombre', 'orden').distinct())
            j.tareas_completadas_count = len(j.tareas_del_dia)
            if j.estado == 'pendiente' and j.tareas_completadas_count > 0:
                total_pendientes_con_evidencia += 1
            j.contrato_vencido = not j.contrato.activo or j.contrato.fecha_fin < hoy

        # Tareas completadas sin jornada registrada (la info no se pierde aunque no haya contrato)
        fechas_con_jornada = set(todas_qs.values_list('fecha', flat=True))
        tareas_completadas = TareaChecklist.objects.filter(
            sede__proyecto=proyecto,
            completado=True,
            participantes=emp,
            activo=True,
        ).select_related('sede').order_by('-fecha_completado')

        agrupadas = defaultdict(list)
        for t in tareas_completadas:
            fecha = t.fecha_completado.date()
            if fecha not in fechas_con_jornada:
                agrupadas[fecha].append(t)

        tareas_sin_jornada = []
        for fecha in sorted(agrupadas.keys(), reverse=True):
            contrato_fecha = emp.contratos_empleado.filter(
                fecha_inicio__lte=fecha, fecha_fin__gte=fecha,
            ).order_by('-created').first()
            tareas_sin_jornada.append({
                'fecha': fecha,
                'tareas': agrupadas[fecha],
                'contrato_fecha': contrato_fecha,
            })

        empleados_data.append({
            'empleado':          emp,
            'contrato':          contrato,
            'jornadas':          jornadas,
            'total_pendientes':  todas_qs.filter(estado='pendiente').count(),
            'tareas_sin_jornada': tareas_sin_jornada,
        })

    return render(request, 'revision_jornadas_proyecto.html', {
        'proyecto': proyecto,
        'empleados_data': empleados_data,
        'estado_filtro': estado_filtro,
        'total_pendientes_con_evidencia': total_pendientes_con_evidencia,
    })


# ── Dashboard instalador ──────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_CAMPO)
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

    # Contrato activo y jornadas de hoy
    contrato_activo = ContratoEmpleado.objects.filter(
        empleado=user, activo=True
    ).order_by('-created').first()

    # Contrato para registrar jornadas: activo si existe, sino el más reciente aunque esté vencido
    contrato_para_jornada = contrato_activo or ContratoEmpleado.objects.filter(
        empleado=user
    ).order_by('-created').first()

    hoy = timezone.localdate()
    contrato_para_jornada_vencido = (
        contrato_para_jornada is not None
        and (not contrato_para_jornada.activo or contrato_para_jornada.fecha_fin < hoy)
    )

    jornadas_hoy = []
    resumen_pago = None
    contrato_resumen = contrato_activo or contrato_para_jornada
    if contrato_resumen:
        jornadas_hoy = JornadaEmpleado.objects.filter(
            contrato=contrato_resumen, fecha=hoy, activo=True
        ).select_related('proyecto')

        jornadas_qs  = contrato_resumen.jornadas.filter(activo=True)
        total_dias   = jornadas_qs.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
        dias_pend    = jornadas_qs.filter(estado='pendiente').aggregate(t=Sum('dias'))['t'] or 0
        dias_pagados = jornadas_qs.filter(estado='aprobada', pago__isnull=False, pago__activo=True, pago__estado='pagado').aggregate(t=Sum('dias'))['t'] or 0
        total_pagado = contrato_resumen.pagos.filter(activo=True, estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
        total_ganado = total_dias * contrato_resumen.monto_diario
        resumen_pago = {
            'total_dias':    total_dias,
            'dias_pend':     dias_pend,
            'dias_pagados':  dias_pagados,
            'dias_por_cobrar': total_dias - dias_pagados,
            'total_ganado':  total_ganado,
            'total_pagado':  total_pagado,
            'saldo':         total_ganado - total_pagado,
        }

    jornadas_recientes = list(
        JornadaEmpleado.objects.filter(
            contrato__empleado=user,
            activo=True,
            fecha__gte=hoy - timedelta(days=29),
        ).select_related('proyecto', 'contrato').order_by('-fecha')
    )
    jr_pendientes  = sum(1 for j in jornadas_recientes if j.estado == 'pendiente')
    jr_rechazadas  = sum(1 for j in jornadas_recientes if j.estado == 'rechazada')
    jr_aprobadas   = sum(1 for j in jornadas_recientes if j.estado == 'aprobada')

    dias_restantes_contrato = None
    pct_tiempo_contrato     = 0
    pct_dias_trabajados     = 0
    if contrato_para_jornada:
        dias_restantes_contrato = (contrato_para_jornada.fecha_fin - hoy).days
        total_cal = max(1, (contrato_para_jornada.fecha_fin - contrato_para_jornada.fecha_inicio).days)
        transcurridos = (hoy - contrato_para_jornada.fecha_inicio).days
        pct_tiempo_contrato = min(100, max(0, round(transcurridos / total_cal * 100)))
        if contrato_para_jornada.dias_laborales:
            dias_trabajados_total = contrato_para_jornada.jornadas.filter(activo=True).aggregate(
                t=Sum('dias'))['t'] or 0
            pct_dias_trabajados = min(100, round(float(dias_trabajados_total) / float(contrato_para_jornada.dias_laborales) * 100))

    return render(request, 'instalador_dashboard.html', {
        'proyectos_data': proyectos_data,
        'mis_tareas_pendientes': mis_tareas_pendientes,
        'no_leidas': user.notificaciones.filter(leida=False).count(),
        'contrato_activo': contrato_activo,
        'contrato_para_jornada': contrato_para_jornada,
        'contrato_para_jornada_vencido': contrato_para_jornada_vencido,
        'jornadas_hoy': jornadas_hoy,
        'hoy': hoy,
        'resumen_pago': resumen_pago,
        'jornadas_recientes': jornadas_recientes,
        'jr_pendientes': jr_pendientes,
        'jr_rechazadas': jr_rechazadas,
        'jr_aprobadas': jr_aprobadas,
        'dias_restantes_contrato': dias_restantes_contrato,
        'pct_tiempo_contrato':     pct_tiempo_contrato,
        'pct_dias_trabajados':     pct_dias_trabajados,
    })


# ── Pagos a empleados ─────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def pagos_empleados_list(request):
    empleado_id     = request.GET.get('empleado_id', '')
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
    if empleado_id:
        qs = qs.filter(contrato__empleado_id=empleado_id)
    if search_proyecto:
        qs = qs.filter(contrato__jornadas__proyecto__nombre__icontains=search_proyecto).distinct()

    paginator = Paginator(qs, per_page)
    pagos_page = paginator.get_page(page)

    total_monto = qs.filter(estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
    total_pendiente_monto = qs.filter(estado='pendiente').aggregate(t=Sum('monto'))['t'] or 0
    contratos_activos = ContratoEmpleado.objects.filter(activo=True).select_related('empleado').order_by('empleado__nombre')
    empleados_con_pagos = (
        Empleado.objects.filter(contratos_empleado__pagos__activo=True)
        .distinct().order_by('nombre', 'apellido_paterno')
    )

    empleados_con_deuda = (
        PagoEmpleado.objects.filter(activo=True, estado='pendiente')
        .values('contrato__empleado_id')
        .distinct()
        .count()
    )

    # Batch: días aprobados y total pagado por contrato (para la página actual)
    contrato_ids = list({p.contrato_id for p in pagos_page.object_list})
    dias_map = {
        d['contrato_id']: float(d['t'] or 0)
        for d in JornadaEmpleado.objects
            .filter(contrato_id__in=contrato_ids, activo=True, estado='aprobada')
            .values('contrato_id').annotate(t=Sum('dias'))
    }
    pagado_map = {
        p['contrato_id']: float(p['t'] or 0)
        for p in PagoEmpleado.objects
            .filter(contrato_id__in=contrato_ids, activo=True, estado='pagado')
            .values('contrato_id').annotate(t=Sum('monto'))
    }
    pagos_data = []
    total_monto_pagina = 0
    for pago in pagos_page.object_list:
        dias       = dias_map.get(pago.contrato_id, 0)
        ganado     = dias * float(pago.contrato.monto_diario)
        confirmado = pagado_map.get(pago.contrato_id, 0)
        total_monto_pagina += float(pago.monto)
        pagos_data.append({
            'obj':    pago,
            'dias':   dias,
            'ganado': ganado,
            'saldo':  ganado - confirmado,
        })

    return render(request, 'pagos_empleados_list.html', {
        'pagos': pagos_page,
        'pagos_data': pagos_data,
        'empleado_id': empleado_id,
        'search_proyecto': search_proyecto,
        'contratos_activos': contratos_activos,
        'empleados_con_pagos': empleados_con_pagos,
        'per_page': per_page,
        'total_monto': total_monto,
        'total_monto_pagina': total_monto_pagina,
        'total_pendiente_monto': total_pendiente_monto,
        'empleados_con_deuda': empleados_con_deuda,
    })


def _contrato_resumen(contrato, excluir_pago_id=None):
    qs = PagoEmpleado.objects.filter(contrato=contrato, activo=True, estado='pagado')
    if excluir_pago_id:
        qs = qs.exclude(pk=excluir_pago_id)
    pagado      = qs.aggregate(t=Sum('monto'))['t'] or 0
    total_dias  = contrato.jornadas.filter(activo=True, estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
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
        contrato=contrato, activo=True, pago__isnull=True, estado='aprobada'
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
        Notificacion.objects.create(
            destinatario=contrato.empleado,
            tipo='general',
            mensaje=f'Se registró un pago de Bs. {pago.monto} a tu cuenta ({pago.get_tipo_pago_display()}).',
        )
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
    resumen  = _contrato_resumen(contrato)
    jornadas_cubiertas  = pago.jornadas_cubiertas.filter(activo=True).select_related('proyecto').order_by('fecha')
    jornadas_pendientes = JornadaEmpleado.objects.filter(
        contrato=contrato, activo=True, pago__isnull=True, estado='aprobada'
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


@login_required
@cargo_required(*ROLES_ADMIN)
def confirmar_pago_empleado(request, id_pago):
    pago     = get_object_or_404(PagoEmpleado, pk=id_pago, activo=True, estado='pendiente')
    contrato = pago.contrato
    resumen  = _contrato_resumen(contrato, excluir_pago_id=pago.id)
    ctx = {
        'pago':        pago,
        'contrato':    contrato,
        'resumen':     resumen,
        'METODOS_PAGO': METODOS_PAGO,
    }
    if request.method == 'POST':
        fecha     = request.POST.get('fecha', '').strip()
        tipo_pago = request.POST.get('tipo_pago', 'efectivo').strip()
        if not fecha:
            messages.error(request, 'La fecha de pago es obligatoria.')
            return render(request, 'confirmar_pago_empleado.html', ctx)
        pago.fecha     = fecha
        pago.tipo_pago = tipo_pago
        pago.estado    = 'pagado'
        pago.save()
        Notificacion.objects.create(
            destinatario=contrato.empleado,
            tipo='general',
            mensaje=f'Se confirmó un pago de Bs. {pago.monto} a tu cuenta ({pago.get_tipo_pago_display()}).',
        )
        messages.success(request, f'Pago de Bs. {pago.monto} confirmado para {contrato.empleado.nombre}.')
        return redirect('pagos_empleados_list')
    return render(request, 'confirmar_pago_empleado.html', ctx)


