from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q, Count, Sum, OuterRef, Subquery
from django.utils import timezone
from django.template.loader import get_template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import Empleado, PagoEmpleado, ContratoEmpleado, JornadaEmpleado
from .forms import EmpleadoForm, ContratoEmpleadoForm, ContratoEmpleadoDesdeEmpleadoForm, JornadaEmpleadoForm, PagoEmpleadoForm
from projects.models import Proyecto, TareaChecklist, ContratoProyecto
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
        messages.success(request, f"El empleado {employee.nombre} {employee.apellido_paterno} fue registrado con acceso al sistema.")
        return redirect('employee_view', employee.id)
    return render(request, 'create_employee.html', {'form': form, 'error': 'Por favor, proporcione datos válidos'})


@login_required
@cargo_required('administrador')
def deactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee, is_active=True)
    if request.method == 'POST':
        empleado.is_active = False
        empleado.activo     = False
        empleado.deleted_at = timezone.now()
        empleado.deleted_by = request.user
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
        total_dias   = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
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
    # ── Tab 1: jornadas pendientes de aprobar ─────────────────────────────────
    jornadas_pend_qs = (
        JornadaEmpleado.objects.filter(activo=True, estado='pendiente')
        .select_related('contrato__empleado', 'proyecto')
        .order_by('contrato__empleado__apellido_paterno', 'fecha')
    )
    pendientes_map = {}
    for j in jornadas_pend_qs:
        emp = j.contrato.empleado
        if emp.id not in pendientes_map:
            pendientes_map[emp.id] = {
                'empleado': emp,
                'contrato': j.contrato,
                'jornadas': [],
                'total_dias': 0,
            }
        pendientes_map[emp.id]['jornadas'].append(j)
        pendientes_map[emp.id]['total_dias'] += j.dias

    # ── Tab 2: jornadas aprobadas sin pago asignado ───────────────────────────
    jornadas_sin_pagar_qs = (
        JornadaEmpleado.objects.filter(activo=True, estado='aprobada', pago__isnull=True)
        .select_related('contrato__empleado', 'proyecto')
        .order_by('contrato__empleado__apellido_paterno', 'fecha')
    )
    sin_pagar_map = {}
    for j in jornadas_sin_pagar_qs:
        emp = j.contrato.empleado
        if emp.id not in sin_pagar_map:
            sin_pagar_map[emp.id] = {
                'empleado': emp,
                'contrato': j.contrato,
                'jornadas': [],
                'total_dias': 0,
                'total_monto': 0,
            }
        sin_pagar_map[emp.id]['jornadas'].append(j)
        sin_pagar_map[emp.id]['total_dias'] += j.dias
        sin_pagar_map[emp.id]['total_monto'] += j.monto

    total_monto_pendiente = sum(g['total_monto'] for g in sin_pagar_map.values())

    return render(request, 'employee_workload.html', {
        'pendientes_por_empleado': list(pendientes_map.values()),
        'sin_pagar_por_empleado': list(sin_pagar_map.values()),
        'total_pendientes': jornadas_pend_qs.count(),
        'total_sin_pagar': jornadas_sin_pagar_qs.count(),
        'total_monto_pendiente': total_monto_pendiente,
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
        empleado = form.save(commit=False)
        empleado.email = form.cleaned_data.get('correo') or ''
        nueva_password = form.cleaned_data.get('password1')
        if nueva_password:
            empleado.set_password(nueva_password)
            update_session_auth_hash(request, empleado)
        empleado.save()
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
            total_pagado = contrato.pagos.filter(activo=True).aggregate(t=Sum('monto'))['t'] or 0
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
            contrato = form.save(commit=False)
            contrato.empleado = empleado
            contrato.save()
            messages.success(request, f'Contrato registrado para {empleado.nombre} {empleado.apellido_paterno}.')
            return redirect('contrato_empleado_detail', id_contrato=contrato.id)
    return render(request, 'create_contrato_desde_empleado.html', {'form': form, 'employee': empleado})


@login_required
@cargo_required(*ROLES_ADMIN)
def contrato_empleado_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
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
def contrato_empleado_pdf(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato)
    context = {
        'contrato': contrato,
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
def create_jornada(request, id_contrato):
    import json
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)
    cargo = getattr(request.user, 'cargo', None)
    if cargo not in ROLES_ADMIN and contrato.empleado != request.user:
        messages.error(request, 'Solo puedes registrar jornadas en tu propio contrato.')
        return redirect('dashboard')
    es_admin = cargo in ROLES_ADMIN

    jornadas        = contrato.jornadas.filter(activo=True).select_related('proyecto').order_by('-fecha')
    total_dias      = jornadas.filter(estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
    total_ganado    = total_dias * contrato.monto_diario
    total_pagado    = contrato.pagos.filter(activo=True).aggregate(t=Sum('monto'))['t'] or 0
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

    return render(request, 'create_jornada.html', {
        'form': form, 'contrato': contrato,
        'jornadas': jornadas, 'total_dias': total_dias,
        'total_ganado': total_ganado, 'total_pagado': total_pagado,
        'saldo_pendiente': saldo_pendiente,
        'from_dashboard': not es_admin,
        'companeros_por_proyecto_json': json.dumps(companeros_por_proyecto),
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
    # Tareas completadas ese día en ese proyecto donde el empleado fue participante
    tareas_del_dia = TareaChecklist.objects.filter(
        sede__proyecto=jornada.proyecto,
        completado=True,
        fecha_completado__date=jornada.fecha,
        participantes=contrato.empleado,
        activo=True,
    ).select_related('sede').order_by('sede__nombre', 'orden')
    return render(request, 'jornada_detail.html', {
        'form': form, 'jornada': jornada, 'contrato': contrato,
        'tareas_del_dia': tareas_del_dia, 'es_admin': es_admin,
    })


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


@login_required
@cargo_required(*ROLES_ADMIN)
def aprobar_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    if request.method == 'POST':
        jornada.estado = 'aprobada'
        jornada.motivo_rechazo = ''
        jornada.save()
        messages.success(request, 'Jornada aprobada.')
    return redirect('revisar_jornadas_proyecto', id_proyecto=jornada.proyecto.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def rechazar_jornada(request, id_jornada):
    jornada = get_object_or_404(JornadaEmpleado, pk=id_jornada, activo=True)
    if request.method == 'POST':
        motivo = request.POST.get('motivo_rechazo', '').strip()
        jornada.estado = 'rechazada'
        jornada.motivo_rechazo = motivo
        jornada.save()
        messages.success(request, 'Jornada rechazada.')
    return redirect('revisar_jornadas_proyecto', id_proyecto=jornada.proyecto.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def revisar_jornadas_proyecto(request, id_proyecto):
    from projects.models import Proyecto
    proyecto = get_object_or_404(Proyecto, pk=id_proyecto, activo=True)

    # Aprobación en lote: aprobar todas las pendientes con evidencia de tareas
    if request.method == 'POST' and request.POST.get('accion') == 'aprobar_con_evidencia':
        pendientes = JornadaEmpleado.objects.filter(
            activo=True, proyecto=proyecto, estado='pendiente',
        ).select_related('contrato__empleado')
        aprobadas = 0
        for j in pendientes:
            tiene_evidencia = TareaChecklist.objects.filter(
                sede__proyecto=proyecto,
                completado=True,
                fecha_completado__date=j.fecha,
                participantes=j.contrato.empleado,
                activo=True,
            ).exists()
            if tiene_evidencia:
                j.estado = 'aprobada'
                j.motivo_rechazo = ''
                j.save()
                aprobadas += 1
        messages.success(request, f'{aprobadas} jornada(s) aprobada(s) automáticamente por evidencia de tareas.')
        return redirect('revisar_jornadas_proyecto', id_proyecto=id_proyecto)

    # Todos los empleados asignados al proyecto
    empleados = proyecto.equipo.filter(is_active=True).order_by('apellido_paterno', 'nombre')

    estado_filtro = request.GET.get('estado', 'pendiente')

    empleados_data = []
    total_pendientes_con_evidencia = 0
    for emp in empleados:
        contrato = emp.contratos_empleado.filter(activo=True).order_by('-created').first()
        if not contrato:
            continue
        qs = contrato.jornadas.filter(activo=True, proyecto=proyecto)
        if estado_filtro in ('pendiente', 'aprobada', 'rechazada'):
            qs = qs.filter(estado=estado_filtro)
        jornadas = list(qs.select_related('registrado_por').order_by('-fecha'))
        # Anotar cada jornada con las tareas completadas ese día por ese empleado
        for j in jornadas:
            j.tareas_del_dia = list(TareaChecklist.objects.filter(
                sede__proyecto=proyecto,
                completado=True,
                fecha_completado__date=j.fecha,
                participantes=emp,
                activo=True,
            ).select_related('sede').order_by('sede__nombre', 'orden'))
            j.tareas_completadas_count = len(j.tareas_del_dia)
            if j.estado == 'pendiente' and j.tareas_completadas_count > 0:
                total_pendientes_con_evidencia += 1
        empleados_data.append({
            'empleado': emp,
            'contrato': contrato,
            'jornadas': jornadas,
            'total_pendientes': contrato.jornadas.filter(activo=True, proyecto=proyecto, estado='pendiente').count(),
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

    hoy = timezone.localdate()
    jornadas_hoy = []
    resumen_pago = None
    if contrato_activo:
        jornadas_hoy = JornadaEmpleado.objects.filter(
            contrato=contrato_activo, fecha=hoy, activo=True
        ).select_related('proyecto')

        total_dias   = contrato_activo.jornadas.filter(activo=True, estado='aprobada').aggregate(t=Sum('dias'))['t'] or 0
        total_pagado = contrato_activo.pagos.filter(activo=True).aggregate(t=Sum('monto'))['t'] or 0
        total_ganado = total_dias * contrato_activo.monto_diario
        resumen_pago = {
            'total_dias':   total_dias,
            'total_ganado': total_ganado,
            'total_pagado': total_pagado,
            'saldo':        total_ganado - total_pagado,
        }

    return render(request, 'instalador_dashboard.html', {
        'proyectos_data': proyectos_data,
        'mis_tareas_pendientes': mis_tareas_pendientes,
        'no_leidas': user.notificaciones.filter(leida=False).count(),
        'contrato_activo': contrato_activo,
        'jornadas_hoy': jornadas_hoy,
        'hoy': hoy,
        'resumen_pago': resumen_pago,
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

    empleados_con_deuda = (
        JornadaEmpleado.objects.filter(activo=True, estado='aprobada', pago__isnull=True)
        .values('contrato__empleado_id')
        .distinct()
        .count()
    )

    return render(request, 'pagos_empleados_list.html', {
        'pagos': pagos_page,
        'search_empleado': search_empleado,
        'search_proyecto': search_proyecto,
        'contratos_activos': contratos_activos,
        'per_page': per_page,
        'total_monto': total_monto,
        'empleados_con_deuda': empleados_con_deuda,
    })


def _contrato_resumen(contrato, excluir_pago_id=None):
    qs = PagoEmpleado.objects.filter(contrato=contrato, activo=True)
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


