from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages

from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError

from .form import ProjectForm, EmpleadoForm, ClienteForm, ProgresoForm, ContratoEmpleadoForm, ContratoProyectoForm
from .models import Proyecto, Empleado, Cliente, Progreso, Contrato, HistorialPresupuesto
from inventario.models import Insumo, Requiere
from pagos.models import Pago, PagoEmpleado
from django.contrib.auth.decorators import login_required
from .decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC, ROLES_CAMPO

from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.db.models import Q, Count, Sum, OuterRef, Subquery, F
from django.db.models.functions import TruncMonth
import json
from datetime import timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from django.views.generic import ListView, CreateView
from django.utils.timezone import now
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def home(request):
    return render(request, 'home.html')


@login_required
@cargo_required(*ROLES_ADMIN)
def signup(request):
    # Registro público deshabilitado: solo administradores pueden acceder.
    # Los empleados se crean desde /employees/create/
    return redirect('employees')


def signout(request):
    if request.method == 'POST':
        logout(request)
    return redirect('landing')




def signin(request):
    # Si ya está autenticado, redirigir según rol
    if request.user.is_authenticated:
        cargo = getattr(request.user, 'cargo', None)
        if cargo in ('instalador', 'tecnico_soporte'):
            return redirect('projects')
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'signin.html', {
            'form': AuthenticationForm()
        })

    user = authenticate(request, username=request.POST.get('username', ''), password=request.POST.get('password', ''))
    if user is None:
        return render(request, 'signin.html', {
            'form': AuthenticationForm(),
            'error': 'Usuario o contraseña incorrectos.'
        })

    login(request, user)
    # Respetar ?next= si viene de @login_required
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    # Redirigir según cargo
    cargo = getattr(user, 'cargo', None)
    if cargo in ('instalador', 'tecnico_soporte'):
        return redirect('projects')
    return redirect('dashboard')


@login_required
def cambiar_contrasena(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantiene la sesión activa
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('cambiar_contrasena')
    else:
        form = PasswordChangeForm(request.user)

    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control form-control-sm'})

    return render(request, 'cambiar_contrasena.html', {'form': form})


def csrf_failure(request, reason=""):
    """
    Vista personalizada para fallos de CSRF.
    En lugar de mostrar la página de error de Django, redirige al login
    con un mensaje claro. Ocurre típicamente cuando la sesión expiró y
    el usuario intenta enviar un formulario con un token antiguo.
    """
    messages.error(
        request,
        "Tu sesión expiró o la página quedó desactualizada. "
        "Por favor inicia sesión nuevamente."
    )
    return redirect('signin')


@login_required
def extend_session(request):
    """
    View to extend the user session. Called via AJAX (POST) when user wants to extend their session.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    request.session.set_expiry(1800)  # 30 minutes from now
    return JsonResponse({'status': 'success', 'message': 'Session extended'})


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def reporte_analisis_view(request):
    total_completados = Proyecto.objects.filter(estado_proyecto='completado').count()
    total_en_progreso = Proyecto.objects.filter(estado_proyecto='en_progreso').count()
    total_pendientes = Proyecto.objects.filter(estado_proyecto='pendiente').count()
    labels = ['Completado', 'En Progreso', 'Pendiente']
    sizes = [total_completados, total_en_progreso, total_pendientes]
    colors = ['#4CAF50', '#FFEB3B', '#F44336']
    explode = (0.1, 0, 0)

    plt.figure(figsize=(4, 4))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, explode=explode)
    plt.axis('equal')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')

    context = {'graphic': graphic}
    return render(request, 'reporte_analisis.html', context)


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def project_analysis(request):
    projects = Proyecto.objects.filter(activo=True)
    total = projects.count()

    if total == 0:
        return render(request, 'project_analysis.html', {'message': "No existen proyectos registrados."})

    # ── Por tipo ──────────────────────────────────────────────────────────────
    tipo_counts = {
        item['tipo_proyecto']: item['total']
        for item in projects.values('tipo_proyecto').annotate(total=Count('tipo_proyecto'))
    }
    instalacion_count   = tipo_counts.get('instalacion_nueva', 0)
    ampliacion_count    = tipo_counts.get('ampliacion', 0)
    mantenimiento_count = tipo_counts.get('mantenimiento', 0)
    emergencia_count    = tipo_counts.get('emergencia', 0)

    # ── Por estado del proyecto ───────────────────────────────────────────────
    estado_counts = {
        item['estado_proyecto']: item['total']
        for item in projects.values('estado_proyecto').annotate(total=Count('estado_proyecto'))
    }
    pendiente_count   = estado_counts.get('pendiente', 0)
    en_progreso_count = estado_counts.get('en_progreso', 0)
    completado_count  = estado_counts.get('completado', 0)

    # ── Por estado de pago ────────────────────────────────────────────────────
    pago_counts = {
        item['estado_pago']: item['total']
        for item in projects.values('estado_pago').annotate(total=Count('estado_pago'))
    }
    no_pagado_count = pago_counts.get('no_pagado', 0)
    parcial_count   = pago_counts.get('parcial', 0)
    pagado_count    = pago_counts.get('pagado', 0)

    # ── Proyectos por mes (últimos 12 meses) ──────────────────────────────────
    MESES_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    doce_meses_atras = timezone.now() - timedelta(days=365)
    monthly_qs = (
        projects.filter(created__gte=doce_meses_atras)
        .annotate(mes=TruncMonth('created'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    monthly_labels = [f"{MESES_ES[m['mes'].month - 1]} {m['mes'].year}" for m in monthly_qs]
    monthly_values = [m['total'] for m in monthly_qs]

    context = {
        'total': total,
        'instalacion_count': instalacion_count,
        'ampliacion_count': ampliacion_count,
        'mantenimiento_count': mantenimiento_count,
        'emergencia_count': emergencia_count,
        'pendiente_count': pendiente_count,
        'en_progreso_count': en_progreso_count,
        'completado_count': completado_count,
        'no_pagado_count': no_pagado_count,
        'parcial_count': parcial_count,
        'pagado_count': pagado_count,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_values': json.dumps(monthly_values),
    }
    return render(request, 'project_analysis.html', context)


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def project_report(request):
    project_type       = request.GET.get('project_type') or None
    project_status     = request.GET.get('project_status') or None
    filter_estado_pago = request.GET.get('filter_estado_pago') or None
    filter_cumplimiento = request.GET.get('filter_cumplimiento') or None
    search_nombre      = request.GET.get('search_nombre', '').strip()
    hoy = timezone.now().date()

    ultimo_avance_qs = Progreso.objects.filter(
        proyecto=OuterRef('pk'), activo=True
    ).order_by('-fecha', '-id').values('porcentaje')[:1]

    projects = Proyecto.objects.filter(activo=True).select_related('cliente').annotate(
        monto_cobrado=Sum('pagos__monto', filter=Q(pagos__activo=True)),
        ultimo_avance=Subquery(ultimo_avance_qs),
    ).order_by('-id')

    if search_nombre:
        projects = projects.filter(nombre__icontains=search_nombre)
    if project_type:
        projects = projects.filter(tipo_proyecto=project_type)
    if project_status:
        projects = projects.filter(estado_proyecto=project_status)
    if filter_estado_pago:
        projects = projects.filter(estado_pago=filter_estado_pago)
    if filter_cumplimiento == 'vencido':
        projects = projects.filter(
            estado_proyecto__in=['pendiente', 'en_progreso'],
            fecha_fin__isnull=False, fecha_fin__lt=hoy,
        )
    elif filter_cumplimiento == 'en_plazo':
        projects = projects.filter(
            estado_proyecto__in=['pendiente', 'en_progreso'],
            fecha_fin__isnull=False, fecha_fin__gte=hoy,
        )
    elif filter_cumplimiento == 'sin_fecha':
        projects = projects.filter(
            estado_proyecto__in=['pendiente', 'en_progreso'],
            fecha_fin__isnull=True,
        )

    agg = projects.aggregate(
        total_monto=Sum('monto_total'),
        total_cobrado=Sum('pagos__monto', filter=Q(pagos__activo=True)),
    )
    monto_total          = agg['total_monto'] or 0
    total_cobrado        = agg['total_cobrado'] or 0
    total_saldo          = monto_total - total_cobrado
    count_completado     = projects.filter(estado_proyecto='completado').count()
    count_en_progreso    = projects.filter(estado_proyecto='en_progreso').count()
    count_pendiente      = projects.filter(estado_proyecto='pendiente').count()

    # Pre-compute saldo y cumplimiento por proyecto
    projects_list = list(projects)
    for p in projects_list:
        p.monto_saldo = p.monto_total - (p.monto_cobrado or 0)
        if p.estado_proyecto == 'completado':
            p.cumplimiento = 'completado'
            p.dias_info = None
        elif not p.fecha_fin:
            p.cumplimiento = 'sin_fecha'
            p.dias_info = None
        elif p.fecha_fin < hoy:
            p.cumplimiento = 'vencido'
            p.dias_info = (hoy - p.fecha_fin).days
        else:
            p.cumplimiento = 'en_plazo'
            p.dias_info = (p.fecha_fin - hoy).days

    count_vencidos   = sum(1 for p in projects_list if p.cumplimiento == 'vencido')
    count_en_plazo   = sum(1 for p in projects_list if p.cumplimiento == 'en_plazo')
    count_sin_fecha  = sum(1 for p in projects_list if p.cumplimiento == 'sin_fecha')

    context = {
        'projects': projects_list,
        'project_type': project_type,
        'project_status': project_status,
        'filter_estado_pago': filter_estado_pago,
        'filter_cumplimiento': filter_cumplimiento,
        'search_nombre': search_nombre,
        'monto_total': monto_total,
        'total_cobrado': total_cobrado,
        'total_saldo': total_saldo,
        'count_completado': count_completado,
        'count_en_progreso': count_en_progreso,
        'count_pendiente': count_pendiente,
        'count_vencidos': count_vencidos,
        'count_en_plazo': count_en_plazo,
        'count_sin_fecha': count_sin_fecha,
        'now': timezone.now(),
        'generado_por': request.user.get_full_name() or request.user.username,
    }

    if 'pdf' in request.GET:
        template = get_template('project_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="reporte_proyectos.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    if 'excel' in request.GET:
        NUM_COLS = 11
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Proyectos'

        # ── Estilos con colores SOBOTEC ──
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

        # Fila 1 — título
        ws.append(['Reporte de Proyectos — SOBOTEC S.R.L.'])
        ws.merge_cells(f'A1:{openpyxl.utils.get_column_letter(NUM_COLS)}1')
        ws['A1'].font      = title_font
        ws['A1'].fill      = title_fill
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 26

        # Fila 2 — generado por + filtros
        gen_por = request.user.get_full_name() or request.user.username
        info_str = f'Generado por: {gen_por}  |  Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        if search_nombre:      info_str += f'  |  Nombre: {search_nombre}'
        if project_type:       info_str += f'  |  Tipo: {project_type}'
        if project_status:     info_str += f'  |  Estado: {project_status}'
        if filter_estado_pago: info_str += f'  |  Pago: {filter_estado_pago}'
        ws.append([info_str])
        ws.merge_cells(f'A2:{openpyxl.utils.get_column_letter(NUM_COLS)}2')
        ws['A2'].font      = info_font
        ws['A2'].fill      = info_fill
        ws['A2'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[2].height = 18

        # Fila 3 — separador
        ws.append([])
        ws.row_dimensions[3].height = 6

        # Fila 4 — encabezados
        headers = ['Código', 'Nombre del Proyecto', 'Cliente', 'Tipo', 'Estado',
                   '% Avance', 'Estado Pago', 'Monto (Bs.)', 'Cobrado (Bs.)', 'Saldo (Bs.)', 'Fecha Inicio']
        ws.append(headers)
        for cell in ws[4]:
            cell.font = header_font; cell.fill = header_fill
            cell.alignment = center; cell.border = cell_border
        ws.row_dimensions[4].height = 22

        # Filas de datos
        last_row = 4
        for i, p in enumerate(projects_list, start=5):
            cobrado = p.monto_cobrado or 0
            saldo   = p.monto_total - cobrado
            ws.append([
                p.codigo,
                p.nombre,
                f'{p.cliente.nombre} {p.cliente.apellido_paterno}' if p.cliente else '—',
                p.get_tipo_proyecto_display(),
                p.get_estado_proyecto_display(),
                f'{p.ultimo_avance or 0}%',
                p.get_estado_pago_display(),
                float(p.monto_total),
                float(cobrado),
                float(saldo),
                p.fecha_inicio.strftime('%d/%m/%Y') if p.fecha_inicio else '—',
            ])
            row_fill = alt_fill if i % 2 == 0 else None
            for j, cell in enumerate(ws[i], start=1):
                if row_fill: cell.fill = row_fill
                cell.border = cell_border
                if j in (8, 9, 10):
                    cell.alignment = right_al; cell.number_format = money_fmt
                elif j == 6:
                    cell.alignment = center
                else:
                    cell.alignment = left
            ws.row_dimensions[i].height = 16
            last_row = i

        # Fila de totales
        total_row = last_row + 1
        ws.append(['', 'TOTAL', '', '', '', '', '',
                   float(monto_total), float(total_cobrado), float(total_saldo), ''])
        for j, cell in enumerate(ws[total_row], start=1):
            cell.font = total_font; cell.fill = total_fill; cell.border = total_border
            if j in (8, 9, 10):
                cell.alignment = right_al; cell.number_format = money_fmt
            else:
                cell.alignment = left
        ws.row_dimensions[total_row].height = 18

        # Anchos de columna
        col_widths = [10, 32, 26, 16, 14, 10, 14, 14, 14, 12, 12]
        for col_idx, width in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        ws.freeze_panes = 'A5'
        ws.auto_filter.ref = f'A4:{openpyxl.utils.get_column_letter(NUM_COLS)}4'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="reporte_proyectos.xlsx"'
        wb.save(response)
        return response

    return render(request, 'project_report.html', context)


@login_required
def projects(request):
    search_nombre = request.GET.get('search_nombre', '')
    filter_estado = request.GET.get('filter_estado', '')
    filter_tipo = request.GET.get('filter_tipo', '')
    filter_pago = request.GET.get('filter_pago', '')
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10

    qs = Proyecto.objects.filter(activo=True).select_related('cliente').order_by('-created')

    # Instalador/Técnico solo ve proyectos donde tiene Contrato activo
    cargo = getattr(request.user, 'cargo', None)
    if cargo in ('instalador', 'tecnico_soporte'):
        qs = qs.filter(contratos__empleado=request.user, contratos__tipo='empleado', contratos__activo=True).distinct()

    if search_nombre:
        qs = qs.filter(nombre__icontains=search_nombre)
    if filter_estado:
        qs = qs.filter(estado_proyecto=filter_estado)
    if filter_tipo:
        qs = qs.filter(tipo_proyecto=filter_tipo)
    if filter_pago:
        qs = qs.filter(estado_pago=filter_pago)

    paginator = Paginator(qs, per_page)
    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

    context = {
        'projects': projects_page,
        'search_nombre': search_nombre,
        'filter_estado': filter_estado,
        'filter_tipo': filter_tipo,
        'filter_pago': filter_pago,
        'per_page': per_page,
    }
    return render(request, 'projects.html', context)


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_project(request, id_project):
    project = get_object_or_404(Proyecto, id=id_project)
    if request.method == 'POST':
        project.activo = False
        project.deleted_at = timezone.now()
        project.deleted_by = request.user
        project.save()
    return redirect('projects')



@login_required
@cargo_required(*ROLES_ADMIN)
def project_detail(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'GET':
        form = ProjectForm(instance=project)
        return render(request, 'project_detail.html', {'project': project, 'form': form})
    else:
        try:
            form = ProjectForm(request.POST, instance=project)
            project = form.save(commit=False)
            project._current_user = request.user
            project.save()
            return redirect('projects')
        except ValueError:
            return render(request, 'project_detail.html', {'project': project, 'form': form, 'error': "Error al actualizar el proyecto"})


@login_required
def project_view(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    progresos = project.progresos.filter(activo=True).order_by('-fecha', '-created')
    ultimo_progreso = progresos.first()
    porcentaje_actual = ultimo_progreso.porcentaje if ultimo_progreso else 0
    contratos_empleados = project.contratos.filter(tipo='empleado', activo=True).select_related('empleado')
    contrato_proyecto = project.contratos.filter(tipo='proyecto', activo=True).first()
    insumos_proyecto = project.insumos.select_related('insumo').order_by('-created')
    total_insumos = sum(r.subtotal for r in insumos_proyecto)

    # ── Pagos a empleados por contrato ─────────────────────────────────────────
    contratos_con_pagos = []
    for contrato in contratos_empleados:
        pagos = contrato.pagos.filter(activo=True).order_by('-fecha')
        total_pagado = pagos.aggregate(total=Sum('monto'))['total'] or 0
        contratos_con_pagos.append({
            'contrato': contrato,
            'pagos': pagos,
            'total_pagado': total_pagado,
            'saldo_pendiente': contrato.monto_acordado - total_pagado,
        })

    # ── Historial de cambios de monto ──────────────────────────────────────────
    historial_monto = HistorialPresupuesto.objects.filter(proyecto=project).order_by('-fecha_modificacion')

    # ── Rentabilidad ───────────────────────────────────────────────────────────
    costo_personal = contratos_empleados.aggregate(total=Sum('monto_acordado'))['total'] or 0
    ingresos = project.monto_total
    rentabilidad = ingresos - total_insumos - costo_personal
    margen = round((rentabilidad / ingresos * 100), 1) if ingresos > 0 else 0
    margen_clamped = max(0, min(100, margen))

    # ── Pagos del cliente al proyecto ──────────────────────────────────────────
    pagos_cliente = project.pagos.filter(activo=True).order_by('fecha')
    total_pagado_cliente = pagos_cliente.aggregate(total=Sum('monto'))['total'] or 0
    saldo_cliente = ingresos - total_pagado_cliente

    context = {
        'project': project,
        'progresos': progresos,
        'porcentaje_actual': porcentaje_actual,
        'contratos_empleados': contratos_empleados,
        'contratos_con_pagos': contratos_con_pagos,
        'contrato_proyecto': contrato_proyecto,
        'insumos_proyecto': insumos_proyecto,
        'total_insumos': total_insumos,
        'costo_personal': costo_personal,
        'ingresos': ingresos,
        'rentabilidad': rentabilidad,
        'margen': margen,
        'margen_clamped': margen_clamped,
        'historial_monto': historial_monto,
        'pagos_cliente': pagos_cliente,
        'total_pagado_cliente': total_pagado_cliente,
        'saldo_cliente': saldo_cliente,
        'now': timezone.now(),
        'generado_por': request.user.get_full_name() or request.user.username,
    }

    if 'pdf' in request.GET:
        template = get_template('project_detail_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        filename = f"ficha_{project.codigo}.pdf"
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    return render(request, 'project_view.html', context)


@login_required
@cargo_required(*ROLES_ADMIN)
def project_complete(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        project.estado_proyecto = 'completado'
        project.fecha_fin = timezone.now().date()
        project.save(update_fields=['estado_proyecto', 'fecha_fin'])
        return redirect('projects')


@login_required
@cargo_required(*ROLES_ADMIN)
def project_delete(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        project.delete()
        return redirect('projects')


@login_required
@cargo_required(*ROLES_ADMIN)
def create_project(request):
    if request.method == 'GET':
        return render(request, 'create_project.html', {
            'form': ProjectForm(),
            'contrato_form': ContratoProyectoForm(),
        })

    form = ProjectForm(request.POST)
    contrato_form = ContratoProyectoForm(request.POST, request.FILES)
    adjuntar_contrato = request.POST.get('adjuntar_contrato') == 'on'

    if form.is_valid():
        if adjuntar_contrato and not contrato_form.is_valid():
            return render(request, 'create_project.html', {
                'form': form,
                'contrato_form': contrato_form,
                'adjuntar_contrato': True,
            })

        project = form.save(commit=False)
        project.creado_por = request.user
        project.save()

        if adjuntar_contrato:
            contrato = contrato_form.save(commit=False)
            contrato.tipo = 'proyecto'
            contrato.proyecto = project
            contrato.save()
            # El contrato sobreescribe el monto estimado ingresado
            project.monto_total = contrato.monto_acordado
            project.save(update_fields=['monto_total'])

        messages.success(request, f'Proyecto "{project.nombre}" creado correctamente.')
        return redirect('project_view', id_project=project.id)

    return render(request, 'create_project.html', {
        'form': form,
        'contrato_form': contrato_form,
        'adjuntar_contrato': adjuntar_contrato,
    })


@login_required
@cargo_required('administrador')
def create_employee(request):
    if request.method == 'GET':
        return render(request, 'create_employee.html', {'form': EmpleadoForm()})
    else:
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.username = form.cleaned_data['username']
            employee.email = form.cleaned_data.get('correo') or ''
            employee.set_password(form.cleaned_data['password1'])
            employee.save()
            messages.success(request, f"El empleado {employee.nombre} {employee.apellido_paterno} fue registrado con acceso al sistema.")
            return redirect('employees')
        return render(request, 'create_employee.html', {
            'form': form,
            'error': 'Por favor, proporcione datos válidos'
        })


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

    # Contratos con sus pagos
    contratos = empleado.contratos.filter(activo=True).select_related('proyecto').order_by('-created')
    contratos_con_pagos = []
    total_acordado_global = 0
    total_pagado_global   = 0

    for contrato in contratos:
        pagos = contrato.pagos.filter(activo=True).order_by('fecha')
        total_pagado = pagos.aggregate(t=Sum('monto'))['t'] or 0
        saldo        = contrato.monto_acordado - total_pagado
        total_acordado_global += contrato.monto_acordado
        total_pagado_global   += total_pagado
        contratos_con_pagos.append({
            'contrato': contrato,
            'pagos': pagos,
            'total_pagado': total_pagado,
            'saldo': saldo,
        })

    saldo_global = total_acordado_global - total_pagado_global

    context = {
        'employee': empleado,
        'contratos_con_pagos': contratos_con_pagos,
        'total_acordado_global': total_acordado_global,
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
    """Vista de carga de trabajo: muestra cuántos proyectos activos tiene cada empleado."""
    empleados = Empleado.objects.filter(is_active=True).annotate(
        proyectos_activos=Count(
            'contratos',
            filter=Q(
                contratos__tipo='empleado',
                contratos__activo=True,
                contratos__proyecto__estado_proyecto__in=['pendiente', 'en_progreso'],
                contratos__proyecto__activo=True,
            )
        ),
        proyectos_completados=Count(
            'contratos',
            filter=Q(
                contratos__tipo='empleado',
                contratos__activo=True,
                contratos__proyecto__estado_proyecto='completado',
                contratos__proyecto__activo=True,
            )
        ),
        monto_contratos=Sum(
            'contratos__monto_acordado',
            filter=Q(contratos__tipo='empleado', contratos__activo=True)
        ),
    ).order_by('-proyectos_activos', 'nombre')

    # Proyectos activos por empleado (para el detalle)
    empleados_list = list(empleados)
    for emp in empleados_list:
        contratos = list(Contrato.objects.filter(
            empleado=emp,
            tipo='empleado',
            activo=True,
            proyecto__estado_proyecto__in=['pendiente', 'en_progreso'],
            proyecto__activo=True,
        ).select_related('proyecto').order_by('proyecto__estado_proyecto', 'proyecto__nombre'))

        # Adjuntar el contrato del proyecto (tipo='proyecto') para obtener sus fechas
        proyecto_ids = [c.proyecto_id for c in contratos]
        contratos_proyecto_map = {
            cp.proyecto_id: cp
            for cp in Contrato.objects.filter(
                proyecto_id__in=proyecto_ids,
                tipo='proyecto',
                activo=True,
            )
        }
        for c in contratos:
            c.contrato_proyecto = contratos_proyecto_map.get(c.proyecto_id)

        emp.contratos_activos_list = contratos

    context = {'empleados': empleados_list}
    return render(request, 'employee_workload.html', context)


@login_required
@cargo_required('administrador')
def employee_detail(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)
    if request.method == 'GET':
        form = EmpleadoForm(instance=empleado, initial={'correo': empleado.email})
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})
    else:
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
    filter_cargo = request.GET.get('filter_cargo', '')
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10

    empleados = Empleado.objects.filter(is_active=True).order_by('-id')

    if search_nombre:
        empleados = empleados.filter(
            Q(nombre__icontains=search_nombre) |
            Q(apellido_paterno__icontains=search_nombre) |
            Q(apellido_materno__icontains=search_nombre)
        )
    if filter_cargo:
        empleados = empleados.filter(cargo=filter_cargo)

    paginator = Paginator(empleados, per_page)
    employees_page = paginator.get_page(page)

    return render(request, 'employees.html', {
        'employees': employees_page,
        'search_nombre': search_nombre,
        'filter_cargo': filter_cargo,
        'per_page': per_page,
    })



@login_required
def create_cliente(request):
    if request.method == 'GET':
        return render(request, 'crear_cliente.html', {
            'form': ClienteForm()
        })
    else:
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f"El contratante {cliente.nombre} {cliente.apellido_paterno} fue registrado exitosamente.")
            return redirect('clientes')
        return render(request, 'crear_cliente.html', {
            'form': form,
            'error': 'Por favor, proporcione datos válidos'
        })


@login_required
def cliente_view(request, id_cliente):
    cliente_obj = get_object_or_404(Cliente, pk=id_cliente)
    return render(request, 'cliente_view.html', {'cliente': cliente_obj})


@login_required
def cliente_detail(request, id_cliente):
    cliente_obj = get_object_or_404(Cliente, pk=id_cliente)
    if request.method == 'GET':
        form = ClienteForm(instance=cliente_obj)
        return render(request, 'cliente_detalle.html', {'cliente': cliente_obj, 'form': form})
    else:
        form = ClienteForm(request.POST, instance=cliente_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"El contratante {cliente_obj.nombre} {cliente_obj.apellido_paterno} fue actualizado exitosamente.")
            return redirect('clientes')
        return render(request, 'cliente_detalle.html', {'cliente': cliente_obj, 'form': form, 'error': "Error al actualizar el contratante"})


@login_required
def clientes(request):
    # Get filter parameters from request
    search_nit_ci = request.GET.get('search_nit_ci', '')
    search_nombre = request.GET.get('search_nombre', '')
    filter_tipo = request.GET.get('filter_tipo', '')
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    
    # Validate page value
    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    
    # Validate per_page value
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    # Start with all clients
    # clientes = Cliente.objects.all()
    clientes = Cliente.objects.filter(activo=True).order_by('-id')
    # Apply name/apellido search filter
    if search_nombre:
        clientes = clientes.filter(
            Q(nombre__icontains=search_nombre) |
            Q(apellido_paterno__icontains=search_nombre) |
            Q(apellido_materno__icontains=search_nombre)
        )
    
    # Apply NIT/CI search filter
    if search_nit_ci:
        clientes = clientes.filter(nit_ci__icontains=search_nit_ci)
    
    # Apply tipo_contratante filter
    if filter_tipo:
        clientes = clientes.filter(tipo_contratante=filter_tipo)
    
    # Total count before pagination
    total_clientes = clientes.count()
    
    # Pagination with configurable per_page
    paginator = Paginator(clientes, per_page)
    try:
        clientes_page = paginator.page(page)
    except PageNotAnInteger:
        clientes_page = paginator.page(1)
    except EmptyPage:
        clientes_page = paginator.page(paginator.num_pages)
    
    context = {
        'clientes': clientes_page,
        'total_clientes': total_clientes,
        'search_nit_ci': search_nit_ci,
        'search_nombre': search_nombre,
        'filter_tipo': filter_tipo,
        'per_page': per_page,
    }
    return render(request, 'clientes.html', context)


@login_required
def deactivate_cliente(request, id_cliente):
    cliente = get_object_or_404(Cliente, id=id_cliente, activo=True)
    if request.method == 'POST':
        cliente.activo = False
        cliente.deleted_at = timezone.now()
        cliente.deleted_by = request.user
        cliente.save()
        messages.success(request, f"El contratante {cliente.nombre} {cliente.apellido_paterno} ha sido inhabilitado exitosamente.")
    return redirect('clientes')


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard_home(request):
    # Instalador/técnico no tiene acceso al dashboard
    if getattr(request.user, 'cargo', None) in ('instalador', 'tecnico_soporte'):
        return redirect('projects')

    # ── Proyectos ──────────────────────────────────────────────────────────────
    proyectos_qs = Proyecto.objects.filter(activo=True)
    total_proyectos = proyectos_qs.count()
    pendientes      = proyectos_qs.filter(estado_proyecto='pendiente').count()
    en_progreso     = proyectos_qs.filter(estado_proyecto='en_progreso').count()
    completados     = proyectos_qs.filter(estado_proyecto='completado').count()

    # ── Finanzas ───────────────────────────────────────────────────────────────
    total_facturado = proyectos_qs.aggregate(total=Sum('monto_total'))['total'] or 0
    total_cobrado   = Pago.objects.filter(activo=True).aggregate(total=Sum('monto'))['total'] or 0
    por_cobrar      = total_facturado - total_cobrado

    # ── Entidades ──────────────────────────────────────────────────────────────
    total_clientes  = Cliente.objects.filter(activo=True).count()
    total_empleados = Empleado.objects.filter(is_active=True).count()

    # ── Insumos / Stock ────────────────────────────────────────────────────────
    insumos_qs         = Insumo.objects.filter(activo=True)
    total_insumos      = insumos_qs.count()
    insumos_agotados   = list(insumos_qs.filter(stock__lte=0))
    insumos_stock_bajo = list(insumos_qs.filter(stock__gt=0, stock__lte=F('stock_minimo'), stock_minimo__gt=0))
    insumos_criticos   = insumos_agotados + insumos_stock_bajo

    # ── Plazos basados en ContratoProyecto.fecha_fin (el plazo real acordado) ──
    # Nota: Proyecto.fecha_fin se asigna automáticamente al completar (no es el plazo)
    hoy = timezone.now().date()
    en_30_dias = hoy + timedelta(days=30)

    contratos_proyecto_qs = Contrato.objects.filter(
        tipo='proyecto',
        activo=True,
        proyecto__activo=True,
        proyecto__estado_proyecto__in=['pendiente', 'en_progreso'],
    ).select_related('proyecto')

    contratos_vencidos = contratos_proyecto_qs.filter(
        fecha_fin__lt=hoy,
    ).order_by('fecha_fin')
    cnt_vencidos = contratos_vencidos.count()

    # ── Alertas clasificadas por categoría ────────────────────────────────────
    # Categoría 1: Plazos vencidos — 3 sub-grupos por antigüedad
    vencidos_hoy     = []   # venció hoy exacto
    vencidos_semana  = []   # venció hace 1-7 días
    vencidos_antiguo = []   # venció hace más de 7 días

    for c in contratos_vencidos:
        dias = (hoy - c.fecha_fin).days
        entrada = {
            'nombre': c.proyecto.nombre,
            'fecha': c.fecha_fin.strftime('%d/%m/%Y'),
            'estado': c.proyecto.get_estado_proyecto_display(),
            'url': f'/projects/{c.proyecto.id}/view/',
            'dias': dias,
        }
        if dias == 0:
            vencidos_hoy.append(entrada)
        elif dias <= 7:
            vencidos_semana.append(entrada)
        else:
            vencidos_antiguo.append(entrada)

    alertas_plazos = vencidos_hoy + vencidos_semana + vencidos_antiguo

    # Categoría 2: Cobros pendientes de proyectos completados
    alertas_cobros = []
    for p in proyectos_qs.filter(estado_proyecto='completado', estado_pago='no_pagado'):
        alertas_cobros.append({
            'tipo': 'danger',
            'icono': 'bi-cash-coin',
            'msg': f'"{p.nombre}" está completado pero sin cobrar.',
            'url': f'/projects/{p.id}/view/',
        })
    for p in proyectos_qs.filter(estado_proyecto='completado', estado_pago='parcial'):
        alertas_cobros.append({
            'tipo': 'warning',
            'icono': 'bi-cash-coin',
            'msg': f'"{p.nombre}" completado con pago parcial pendiente.',
            'url': f'/projects/{p.id}/view/',
        })

    # Categoría 3: Stock de inventario
    alertas_inventario = []
    for i in insumos_agotados:
        alertas_inventario.append({
            'tipo': 'danger',
            'icono': 'bi-box-seam',
            'msg': f'"{i.nombre}" sin stock disponible (0 unidades).',
            'url': f'/insumos/{i.id}/',
        })
    for i in insumos_stock_bajo:
        alertas_inventario.append({
            'tipo': 'warning',
            'icono': 'bi-box-seam',
            'msg': f'"{i.nombre}" con stock bajo ({i.stock} uds., mínimo {i.stock_minimo}).',
            'url': f'/insumos/{i.id}/',
        })

    # Categoría 4: Pagos pendientes a empleados
    alertas_empleados = []
    pagado_subq = PagoEmpleado.objects.filter(
        contrato=OuterRef('pk'), activo=True
    ).values('contrato').annotate(t=Sum('monto')).values('t')
    contratos_completados = Contrato.objects.filter(
        tipo='empleado', activo=True, proyecto__estado_proyecto='completado'
    ).select_related('empleado', 'proyecto').annotate(
        total_pagado=Subquery(pagado_subq)
    )
    for contrato in contratos_completados:
        pagado = contrato.total_pagado or 0
        if pagado < contrato.monto_acordado:
            pendiente = contrato.monto_acordado - pagado
            alertas_empleados.append({
                'tipo': 'warning',
                'icono': 'bi-person-exclamation',
                'msg': f'{contrato.empleado.nombre} {contrato.empleado.apellido_paterno} tiene Bs. {pendiente:.2f} pendientes en "{contrato.proyecto.nombre}".',
                'url': f'/employees/{contrato.empleado.id}/view/',
            })

    # Categoría 5: Próximos a vencer — 3 sub-grupos por urgencia (ContratoProyecto)
    proximos_hoy     = []   # vence hoy o mañana (0-1 días)
    proximos_semana  = []   # vence esta semana  (2-7 días)
    proximos_mes     = []   # vence este mes     (8-30 días)

    for c in contratos_proyecto_qs.filter(
        fecha_fin__gte=hoy,
        fecha_fin__lte=en_30_dias,
    ).order_by('fecha_fin'):
        dias_restantes = (c.fecha_fin - hoy).days
        entrada = {
            'icono': 'bi-hourglass-split',
            'nombre': c.proyecto.nombre,
            'fecha': c.fecha_fin.strftime('%d/%m/%Y'),
            'estado': c.proyecto.get_estado_proyecto_display(),
            'url': f'/projects/{c.proyecto.id}/view/',
            'dias': dias_restantes,
        }
        if dias_restantes <= 1:
            proximos_hoy.append(entrada)
        elif dias_restantes <= 7:
            proximos_semana.append(entrada)
        else:
            proximos_mes.append(entrada)

    alertas_proximos = proximos_hoy + proximos_semana + proximos_mes

    total_alertas = len(alertas_plazos) + len(alertas_proximos) + len(alertas_cobros) + len(alertas_inventario) + len(alertas_empleados)

    # ── Últimos 5 proyectos ────────────────────────────────────────────────────
    ultimos_proyectos = proyectos_qs.select_related('cliente').order_by('-created')[:5]

    # ── Datos para gráficos (JSON-safe) ───────────────────────────────────────
    tipos_labels = ['Instalación Nueva', 'Ampliación', 'Mantenimiento', 'Emergencia']
    tipos_values = [
        proyectos_qs.filter(tipo_proyecto='instalacion_nueva').count(),
        proyectos_qs.filter(tipo_proyecto='ampliacion').count(),
        proyectos_qs.filter(tipo_proyecto='mantenimiento').count(),
        proyectos_qs.filter(tipo_proyecto='emergencia').count(),
    ]

    context = {
        'total_proyectos':      total_proyectos,
        'pendientes':           pendientes,
        'en_progreso':          en_progreso,
        'completados':          completados,
        'total_facturado':      total_facturado,
        'total_cobrado':        total_cobrado,
        'por_cobrar':           por_cobrar,
        'total_clientes':       total_clientes,
        'total_empleados':      total_empleados,
        'total_insumos':        total_insumos,
        'cnt_agotados':         len(insumos_agotados),
        'cnt_stock_bajo':       len(insumos_stock_bajo),
        'insumos_criticos':     insumos_criticos,
        'alertas_plazos':       alertas_plazos,
        'vencidos_hoy':         vencidos_hoy,
        'vencidos_semana':      vencidos_semana,
        'vencidos_antiguo':     vencidos_antiguo,
        'alertas_proximos':     alertas_proximos,
        'proximos_hoy':         proximos_hoy,
        'proximos_semana':      proximos_semana,
        'proximos_mes':         proximos_mes,
        'alertas_cobros':       alertas_cobros,
        'alertas_inventario':   alertas_inventario,
        'alertas_empleados':    alertas_empleados,
        'total_alertas':        total_alertas,
        'cnt_vencidos':         cnt_vencidos,
        'ultimos_proyectos':    ultimos_proyectos,
        'tipos_labels':         tipos_labels,
        'tipos_values':         tipos_values,
    }
    return render(request, 'home.html', context)


# ===================== PROGRESO =====================

@login_required
def create_progreso(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'GET':
        form = ProgresoForm(proyecto=project)
        return render(request, 'create_progreso.html', {'form': form, 'project': project})
    else:
        form = ProgresoForm(request.POST, proyecto=project)
        if form.is_valid():
            progreso = form.save(commit=False)
            progreso.proyecto = project
            progreso.save()

            if progreso.porcentaje == 100 and project.estado_proyecto != 'completado':
                era_pendiente = project.estado_proyecto == 'pendiente'
                project.estado_proyecto = 'completado'
                project.fecha_fin = timezone.now().date()
                if era_pendiente and not project.fecha_inicio:
                    project.fecha_inicio = timezone.now().date()
                project.save(update_fields=['estado_proyecto', 'fecha_fin', 'fecha_inicio'])
                messages.success(request, 'Progreso registrado. El proyecto fue marcado como completado automáticamente.')
            elif 0 < progreso.porcentaje < 100 and project.estado_proyecto == 'pendiente':
                project.estado_proyecto = 'en_progreso'
                project.fecha_inicio = timezone.now().date()
                project.save(update_fields=['estado_proyecto', 'fecha_inicio'])
                messages.success(request, 'Progreso registrado. El proyecto fue marcado como en progreso.')
            else:
                messages.success(request, 'Progreso registrado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_progreso.html', {'form': form, 'project': project})


@login_required
def progreso_detail(request, id_progreso):
    progreso = get_object_or_404(Progreso, pk=id_progreso, activo=True)
    project = progreso.proyecto
    if request.method == 'GET':
        form = ProgresoForm(instance=progreso, proyecto=project)
        return render(request, 'progreso_detail.html', {'form': form, 'progreso': progreso, 'project': project})
    else:
        form = ProgresoForm(request.POST, instance=progreso, proyecto=project)
        if form.is_valid():
            progreso = form.save()
            if progreso.porcentaje == 100 and project.estado_proyecto != 'completado':
                project.estado_proyecto = 'completado'
                project.fecha_fin = timezone.now().date()
                project.save(update_fields=['estado_proyecto', 'fecha_fin'])
                messages.success(request, 'Progreso actualizado. El proyecto fue marcado como completado automáticamente.')
            elif 0 < progreso.porcentaje < 100 and project.estado_proyecto == 'pendiente':
                project.estado_proyecto = 'en_progreso'
                project.fecha_inicio = timezone.now().date()
                project.save(update_fields=['estado_proyecto', 'fecha_inicio'])
                messages.success(request, 'Progreso actualizado. El proyecto fue marcado como en progreso.')
            else:
                messages.success(request, 'Progreso actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'progreso_detail.html', {'form': form, 'progreso': progreso, 'project': project})


@login_required
def deactivate_progreso(request, id_progreso):
    progreso = get_object_or_404(Progreso, pk=id_progreso, activo=True)
    id_project = progreso.proyecto.id
    if request.method == 'POST':
        progreso.activo = False
        progreso.deleted_at = timezone.now()
        progreso.deleted_by = request.user
        progreso.save()
        messages.success(request, 'Registro de progreso eliminado.')
    return redirect('project_view', id_project=id_project)


# ===================== CONTRATOS =====================

@login_required
def create_contrato_empleado(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    empleados_data = {
        str(e.id): {
            'cargo': e.get_cargo_display(),
            'celular': e.numero_celular or '—',
        }
        for e in Empleado.objects.filter(is_active=True)
    }
    if request.method == 'GET':
        form = ContratoEmpleadoForm()
        return render(request, 'create_contrato_empleado.html', {'form': form, 'project': project, 'empleados_data': empleados_data})
    else:
        form = ContratoEmpleadoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.tipo = 'empleado'
            contrato.proyecto = project
            contrato.save()
            messages.success(request, f'Contrato registrado para {contrato.empleado.nombre} {contrato.empleado.apellido_paterno}.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_contrato_empleado.html', {'form': form, 'project': project, 'empleados_data': empleados_data})


@login_required
def contrato_empleado_detail(request, id_contrato):
    contrato = get_object_or_404(Contrato, pk=id_contrato, tipo='empleado', activo=True)
    project = contrato.proyecto
    if request.method == 'GET':
        form = ContratoEmpleadoForm(instance=contrato)
        return render(request, 'contrato_empleado_detail.html', {'form': form, 'contrato': contrato, 'project': project})
    else:
        form = ContratoEmpleadoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contrato actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'contrato_empleado_detail.html', {'form': form, 'contrato': contrato, 'project': project})


@login_required
def deactivate_contrato_empleado(request, id_contrato):
    contrato = get_object_or_404(Contrato, pk=id_contrato, tipo='empleado', activo=True)
    if request.method == 'POST':
        contrato.activo = False
        contrato.deleted_at = timezone.now()
        contrato.deleted_by = request.user
        contrato.save()
        messages.success(request, f'Contrato de {contrato.empleado.nombre} {contrato.empleado.apellido_paterno} inhabilitado.')
    return redirect('project_view', id_project=contrato.proyecto.id)


@login_required
def create_contrato_proyecto(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    # Check if project already has an active contract
    existing = project.contratos.filter(tipo='proyecto', activo=True).first()
    if existing:
        messages.warning(request, 'Este proyecto ya tiene un contrato registrado.')
        return redirect('project_view', id_project=project.id)
    if request.method == 'GET':
        form = ContratoProyectoForm()
        return render(request, 'create_contrato_proyecto.html', {'form': form, 'project': project})
    else:
        form = ContratoProyectoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.tipo = 'proyecto'
            contrato.proyecto = project
            contrato.save()
            project.monto_total = contrato.monto_acordado
            project._current_user = request.user
            project.save(update_fields=['monto_total'])
            messages.success(request, 'Contrato del proyecto registrado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_contrato_proyecto.html', {'form': form, 'project': project})


@login_required
def contrato_proyecto_detail(request, id_contrato):
    contrato = get_object_or_404(Contrato, pk=id_contrato, tipo='proyecto', activo=True)
    project = contrato.proyecto
    if request.method == 'GET':
        form = ContratoProyectoForm(instance=contrato)
        return render(request, 'contrato_proyecto_detail.html', {'form': form, 'contrato': contrato, 'project': project})
    else:
        form = ContratoProyectoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            contrato = form.save()
            project.monto_total = contrato.monto_acordado
            project._current_user = request.user
            project.save(update_fields=['monto_total'])
            messages.success(request, 'Contrato del proyecto actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'contrato_proyecto_detail.html', {'form': form, 'contrato': contrato, 'project': project})


@login_required
def deactivate_contrato_proyecto(request, id_contrato):
    contrato = get_object_or_404(Contrato, pk=id_contrato, tipo='proyecto', activo=True)
    if request.method == 'POST':
        contrato.activo = False
        contrato.deleted_at = timezone.now()
        contrato.deleted_by = request.user
        contrato.save()
        messages.success(request, 'Contrato del proyecto inhabilitado.')
    return redirect('project_view', id_project=contrato.proyecto.id)


