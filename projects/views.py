from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError

from .form import ProjectForm, ClienteForm, SedeForm, TareaChecklistForm, PaymentForm
from .models import Proyecto, Cliente, Sede, TareaChecklist, PagoProyecto
from empleados.models import Empleado, ContratoEmpleado, JornadaEmpleado, PagoEmpleado
from inventario.models import Insumo, Requiere
from django.contrib.auth.decorators import login_required
from .decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC, ROLES_CAMPO

from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
plt.rcParams.update({
    'font.family':       'DejaVu Sans',
    'font.size':         6,
    'axes.titlesize':    8,
    'axes.titleweight':  'bold',
    'axes.labelsize':    6,
    'figure.facecolor':  'white',
    'axes.facecolor':    'white',
    'axes.edgecolor':    '#dee2e6',
    'axes.linewidth':    0.8,
    'xtick.color':       '#495057',
    'ytick.color':       '#495057',
    'text.color':        '#212529',
    'grid.color':        '#e9ecef',
    'grid.linewidth':    0.8,
})
import io
import urllib, base64
from django.db.models import Q, Count, Sum, OuterRef, Subquery, F, Max as db_Max, Prefetch, ExpressionWrapper, DecimalField as ModelDecimalField, IntegerField
from django.db import models
from django.db.models.functions import TruncMonth, Coalesce
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime, timedelta, date
from collections import defaultdict
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

    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is None:
        from empleados.models import Empleado as _Empleado
        usuario_existe = _Empleado.objects.filter(username=username).exists()
        error = 'Contraseña incorrecta.' if usuario_existe else 'Usuario no encontrado.'
        return render(request, 'signin.html', {
            'form': AuthenticationForm(),
            'error': error,
            'username_value': username,
        })

    login(request, user)
    # Respetar ?next= si viene de @login_required — validar host para evitar open redirect
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
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
def project_analysis(request):
    MESES_NOMBRES = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ]
    MESES_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

    # ── Filtros de período ─────────────────────────────────────────────────────
    try:
        filtro_anio = int(request.GET.get('anio', '')) or None
    except ValueError:
        filtro_anio = None
    try:
        _mes = int(request.GET.get('mes', ''))
        filtro_mes = _mes if filtro_anio and 1 <= _mes <= 12 else None
    except ValueError:
        filtro_mes = None

    anios_disponibles = sorted(set(
        Proyecto.objects.filter(activo=True).values_list('created__year', flat=True)
    ), reverse=True)
    meses_lista = [{'num': i, 'nombre': MESES_NOMBRES[i]} for i in range(1, 13)]

    if filtro_anio and filtro_mes:
        periodo_label = f'{MESES_NOMBRES[filtro_mes]} {filtro_anio}'
    elif filtro_anio:
        periodo_label = str(filtro_anio)
    else:
        periodo_label = None

    # ── Queryset base filtrado ────────────────────────────────────────────────
    projects = Proyecto.objects.filter(activo=True)
    if filtro_anio:
        projects = projects.filter(created__year=filtro_anio)
        if filtro_mes:
            projects = projects.filter(created__month=filtro_mes)

    total = projects.count()

    if total == 0 and not filtro_anio:
        return render(request, 'project_analysis.html', {
            'message': "No existen proyectos registrados.",
            'anios_disponibles': anios_disponibles, 'meses_lista': meses_lista,
            'filtro_anio': filtro_anio, 'filtro_mes': filtro_mes, 'periodo_label': periodo_label,
        })

    # ── Por tipo ──────────────────────────────────────────────────────────────
    tipo_counts = {
        item['tipo_proyecto']: item['total']
        for item in projects.values('tipo_proyecto').annotate(total=Count('tipo_proyecto'))
    }
    instalacion_count           = tipo_counts.get('instalacion_nueva', 0)
    ampliacion_count            = tipo_counts.get('ampliacion', 0)
    mantenimiento_externo_count = tipo_counts.get('mantenimiento_externo', 0)
    emergencia_count            = tipo_counts.get('emergencia', 0)

    # ── Por estado ────────────────────────────────────────────────────────────
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

    # ── Proyectos por mes ─────────────────────────────────────────────────────
    if filtro_anio:
        # Todos los meses del año seleccionado
        monthly_qs = (
            Proyecto.objects.filter(activo=True, created__year=filtro_anio)
            .annotate(mes=TruncMonth('created'))
            .values('mes').annotate(total=Count('id')).order_by('mes')
        )
        monthly_chart_label = f'Proyectos creados en {filtro_anio}'
    else:
        # Últimos 12 meses
        doce_meses_atras = timezone.now() - timedelta(days=365)
        monthly_qs = (
            Proyecto.objects.filter(activo=True, created__gte=doce_meses_atras)
            .annotate(mes=TruncMonth('created'))
            .values('mes').annotate(total=Count('id')).order_by('mes')
        )
        monthly_chart_label = 'Últimos 12 meses'

    monthly_labels = [f"{MESES_ES[m['mes'].month - 1]} {m['mes'].year}" for m in monthly_qs]
    monthly_values = [m['total'] for m in monthly_qs]

    context = {
        'total':                        total,
        'instalacion_count':           instalacion_count,
        'ampliacion_count':            ampliacion_count,
        'mantenimiento_externo_count': mantenimiento_externo_count,
        'emergencia_count':            emergencia_count,
        'pendiente_count':              pendiente_count,
        'en_progreso_count':            en_progreso_count,
        'completado_count':             completado_count,
        'no_pagado_count':              no_pagado_count,
        'parcial_count':                parcial_count,
        'pagado_count':                 pagado_count,
        'monthly_chart_label':          monthly_chart_label,
        'monthly_labels':               json.dumps(monthly_labels),
        'monthly_values':               json.dumps(monthly_values),
        'filtro_anio':                  filtro_anio,
        'filtro_mes':                   filtro_mes,
        'anios_disponibles':            anios_disponibles,
        'meses_lista':                  meses_lista,
        'periodo_label':                periodo_label,
    }
    return render(request, 'project_analysis.html', context)


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def project_report(request):
    project_type        = request.GET.get('project_type') or None
    project_status      = request.GET.get('project_status') or None
    filter_estado_pago  = request.GET.get('filter_estado_pago') or None
    filter_cumplimiento = request.GET.get('filter_cumplimiento') or None
    search_nombre       = request.GET.get('search_nombre', '').strip()
    fecha_desde         = request.GET.get('fecha_desde', '').strip()
    fecha_hasta         = request.GET.get('fecha_hasta', '').strip()
    per_page = int(request.GET.get('per_page', 20))
    if per_page not in (10, 20, 50, 100):
        per_page = 20
    page = request.GET.get('page', 1)
    hoy = timezone.now().date()


    sedes_prefetch = Prefetch(
        'sedes',
        queryset=Sede.objects.filter(activo=True).prefetch_related(
            Prefetch('tareas', queryset=TareaChecklist.objects.filter(activo=True))
        ),
        to_attr='sedes_activas',
    )

    projects = Proyecto.objects.filter(activo=True).select_related('cliente').prefetch_related(sedes_prefetch).annotate(
        monto_cobrado=Sum('pagos__monto', filter=Q(pagos__activo=True)),
        contrato_fecha_inicio=Subquery(contrato_fecha_inicio_qs),
        contrato_fecha_fin=Subquery(contrato_fecha_fin_qs),
        num_empleados=Count('equipo', distinct=True),
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
            contrato_fecha_fin__isnull=False, contrato_fecha_fin__lt=hoy,
        )
    elif filter_cumplimiento == 'en_plazo':
        projects = projects.filter(
            estado_proyecto__in=['pendiente', 'en_progreso'],
            contrato_fecha_fin__isnull=False, contrato_fecha_fin__gte=hoy,
        )
    elif filter_cumplimiento == 'sin_fecha':
        projects = projects.filter(
            estado_proyecto__in=['pendiente', 'en_progreso'],
            contrato_fecha_fin__isnull=True,
        )
    if fecha_desde:
        try:
            projects = projects.filter(contrato_fecha_inicio__gte=datetime.strptime(fecha_desde, '%Y-%m-%d').date())
        except ValueError:
            fecha_desde = ''
    if fecha_hasta:
        try:
            projects = projects.filter(contrato_fecha_inicio__lte=datetime.strptime(fecha_hasta, '%Y-%m-%d').date())
        except ValueError:
            fecha_hasta = ''

    # Agregados sobre el total filtrado (para KPIs y totales de PDF/Excel)
    agg = projects.aggregate(
        total_monto=Sum('monto_total'),
        total_cobrado=Sum('pagos__monto', filter=Q(pagos__activo=True)),
    )
    monto_total       = agg['total_monto'] or 0
    total_cobrado     = agg['total_cobrado'] or 0
    total_saldo       = monto_total - total_cobrado
    count_completado  = projects.filter(estado_proyecto='completado').count()
    count_en_progreso = projects.filter(estado_proyecto='en_progreso').count()
    count_pendiente   = projects.filter(estado_proyecto='pendiente').count()

    def _annotate_projects(qs_items):
        """Agrega atributos calculados a cada proyecto de la lista."""
        result = []
        for p in qs_items:
            p.monto_saldo = p.monto_total - (p.monto_cobrado or 0)
            sedes_list_p = p.sedes_activas
            p.ultimo_avance = (
                round(sum(s.porcentaje_checklist for s in sedes_list_p) / len(sedes_list_p))
                if sedes_list_p else 0
            )
            fecha_fin_contrato = p.contrato_fecha_fin
            if p.estado_proyecto == 'completado':
                p.cumplimiento = 'completado'
                p.dias_info = None
            elif not fecha_fin_contrato:
                p.cumplimiento = 'sin_fecha'
                p.dias_info = None
            elif fecha_fin_contrato < hoy:
                p.cumplimiento = 'vencido'
                p.dias_info = (hoy - fecha_fin_contrato).days
            else:
                p.cumplimiento = 'en_plazo'
                p.dias_info = (fecha_fin_contrato - hoy).days
            result.append(p)
        return result

    # Conteos de cumplimiento via BD (evita evaluar la queryset completa en Python)
    activos_qs = projects.filter(estado_proyecto__in=['pendiente', 'en_progreso'])
    count_vencidos  = activos_qs.filter(contrato_fecha_fin__isnull=False, contrato_fecha_fin__lt=hoy).count()
    count_en_plazo  = activos_qs.filter(contrato_fecha_fin__isnull=False, contrato_fecha_fin__gte=hoy).count()
    count_sin_fecha = activos_qs.filter(contrato_fecha_fin__isnull=True).count()

    # PDF / Excel: lista completa sin paginar
    if 'pdf' in request.GET or 'excel' in request.GET:
        projects_list = _annotate_projects(list(projects))
        projects_page = None
    else:
        # Paginación solo para la vista HTML
        paginator = Paginator(projects, per_page)
        try:
            projects_page = paginator.page(page)
        except PageNotAnInteger:
            projects_page = paginator.page(1)
        except EmptyPage:
            projects_page = paginator.page(paginator.num_pages)
        projects_list = _annotate_projects(list(projects_page.object_list))

    context = {
        'projects': projects_list,
        'projects_page': projects_page,
        'project_type': project_type,
        'project_status': project_status,
        'filter_estado_pago': filter_estado_pago,
        'filter_cumplimiento': filter_cumplimiento,
        'search_nombre': search_nombre,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'per_page': per_page,
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
                p.contrato_fecha_inicio.strftime('%d/%m/%Y') if p.contrato_fecha_inicio else '—',
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
    search_nombre        = request.GET.get('search_nombre', '')
    filter_estado        = request.GET.get('filter_estado', '')
    filter_tipo          = request.GET.get('filter_tipo', '')
    filter_pago          = request.GET.get('filter_pago', '')
    fecha_inicio_desde   = request.GET.get('fecha_inicio_desde', '')
    fecha_inicio_hasta   = request.GET.get('fecha_inicio_hasta', '')
    fecha_fin_desde      = request.GET.get('fecha_fin_desde', '')
    fecha_fin_hasta      = request.GET.get('fecha_fin_hasta', '')
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

    # Instalador/Técnico solo ve proyectos donde es miembro del equipo
    cargo = getattr(request.user, 'cargo', None)
    if cargo in ('instalador', 'tecnico_soporte'):
        qs = qs.filter(equipo=request.user).distinct()

    if search_nombre:
        qs = qs.filter(nombre__icontains=search_nombre)
    if filter_estado:
        qs = qs.filter(estado_proyecto=filter_estado)
    if filter_tipo:
        qs = qs.filter(tipo_proyecto=filter_tipo)
    if filter_pago:
        qs = qs.filter(estado_pago=filter_pago)

    # Filtros de rango de fechas (ignorar valores vacíos o malformados)
    if fecha_inicio_desde:
        try:
            qs = qs.filter(fecha_inicio__gte=datetime.strptime(fecha_inicio_desde, '%Y-%m-%d').date())
        except ValueError:
            fecha_inicio_desde = ''
    if fecha_inicio_hasta:
        try:
            qs = qs.filter(fecha_inicio__lte=datetime.strptime(fecha_inicio_hasta, '%Y-%m-%d').date())
        except ValueError:
            fecha_inicio_hasta = ''
    if fecha_fin_desde:
        try:
            qs = qs.filter(fecha_fin__gte=datetime.strptime(fecha_fin_desde, '%Y-%m-%d').date())
        except ValueError:
            fecha_fin_desde = ''
    if fecha_fin_hasta:
        try:
            qs = qs.filter(fecha_fin__lte=datetime.strptime(fecha_fin_hasta, '%Y-%m-%d').date())
        except ValueError:
            fecha_fin_hasta = ''

    _total_sq = (
        TareaChecklist.objects
        .filter(sede__proyecto=OuterRef('pk'), sede__activo=True, activo=True)
        .order_by().values('sede__proyecto')
        .annotate(n=Count('id')).values('n')
    )
    _ok_sq = (
        TareaChecklist.objects
        .filter(sede__proyecto=OuterRef('pk'), sede__activo=True, activo=True, completado=True)
        .order_by().values('sede__proyecto')
        .annotate(n=Count('id')).values('n')
    )
    qs = qs.annotate(
        total_tareas=Coalesce(Subquery(_total_sq, output_field=IntegerField()), 0),
        tareas_ok=Coalesce(Subquery(_ok_sq, output_field=IntegerField()), 0),
    )

    paginator = Paginator(qs, per_page)
    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

    # Calcula el progreso usando promedio por sede (igual que project_view) para evitar
    # inconsistencia: la cuenta plana de tareas ignora sedes sin tareas asignadas.
    _page_ids = [p.id for p in projects_page]
    _sedes_qs = Sede.objects.filter(
        proyecto_id__in=_page_ids, activo=True
    ).prefetch_related(
        Prefetch('tareas', queryset=TareaChecklist.objects.filter(activo=True), to_attr='tareas_activas')
    )
    _sedes_map = {}
    for _s in _sedes_qs:
        _sedes_map.setdefault(_s.proyecto_id, []).append(_s)

    for _p in projects_page:
        _sedes = _sedes_map.get(_p.id, [])
        if _sedes:
            _total_pct = sum(
                (round(sum(1 for _t in _s.tareas_activas if _t.completado) / len(_s.tareas_activas) * 100)
                 if _s.tareas_activas else 0)
                for _s in _sedes
            )
            _p.ultimo_avance = round(_total_pct / len(_sedes))
        else:
            _p.ultimo_avance = None

    context = {
        'projects':            projects_page,
        'search_nombre':       search_nombre,
        'filter_estado':       filter_estado,
        'filter_tipo':         filter_tipo,
        'filter_pago':         filter_pago,
        'fecha_inicio_desde':  fecha_inicio_desde,
        'fecha_inicio_hasta':  fecha_inicio_hasta,
        'fecha_fin_desde':     fecha_fin_desde,
        'fecha_fin_hasta':     fecha_fin_hasta,
        'per_page':            per_page,
        'today':               timezone.now().date(),
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
        project._current_user = request.user
        project.save()
        messages.success(request, f'El proyecto "{project.nombre}" fue desactivado exitosamente.')
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
    insumos_proyecto = project.insumos.select_related('insumo').order_by('-created')
    total_insumos = sum(r.costo_total for r in insumos_proyecto)

    # ── Equipo del proyecto con estadísticas de jornadas ──────────────────────
    miembros = project.equipo.filter(is_active=True)
    jornadas_agg = (
        JornadaEmpleado.objects
        .filter(proyecto=project, activo=True)
        .values('contrato__empleado_id')
        .annotate(
            dias_aprobados=Sum('dias', filter=Q(estado='aprobada')),
            dias_pendientes=Sum('dias', filter=Q(estado='pendiente')),
            ultima_fecha=db_Max('fecha'),
            costo_aprobado=Sum(
                F('dias') * F('contrato__monto_acordado') / F('contrato__dias_laborales'),
                filter=Q(estado='aprobada')
            ),
        )
    )
    jornadas_map = {j['contrato__empleado_id']: j for j in jornadas_agg}

    equipo_proyecto = []
    costo_personal = 0
    _cargo_orden = {'instalador': 0, 'tecnico_soporte': 1}
    for emp in sorted(miembros, key=lambda e: _cargo_orden.get(e.cargo, 2)):
        j = jornadas_map.get(emp.pk, {})
        dias_aprobados  = j.get('dias_aprobados')  or 0
        dias_pendientes = j.get('dias_pendientes') or 0
        costo = j.get('costo_aprobado') or 0
        costo_personal += costo
        equipo_proyecto.append({
            'empleado':        emp,
            'dias_aprobados':  dias_aprobados,
            'dias_pendientes': dias_pendientes,
            'costo':           costo,
            'ultima_fecha':    j.get('ultima_fecha'),
        })
    empleados_disponibles = Empleado.objects.filter(is_active=True).exclude(
        pk__in=miembros.values_list('pk', flat=True)
    ).order_by('apellido_paterno')

    # ── Rentabilidad ───────────────────────────────────────────────────────────
    ingresos = project.monto_total
    rentabilidad = ingresos - total_insumos - costo_personal
    margen = round((rentabilidad / ingresos * 100), 1) if ingresos > 0 else 0
    margen_clamped = int(max(0, min(100, margen)))

    # ── Pagos del cliente ──────────────────────────────────────────────────────
    pagos_cliente = project.pagos.filter(activo=True).order_by('fecha')
    total_pagado_cliente = pagos_cliente.aggregate(total=Sum('monto'))['total'] or 0
    saldo_cliente = ingresos - total_pagado_cliente

    # ── Sedes ──────────────────────────────────────────────────────────────────
    sedes = project.sedes.filter(activo=True).prefetch_related('tareas')
    sedes_geo_json = json.dumps([
        {
            'lat': float(s.latitud), 'lng': float(s.longitud),
            'nombre': s.nombre, 'direccion': s.direccion,
            'estado': s.estado,
            'url': f'/sedes/{s.id}/ver/',
        }
        for s in sedes if s.latitud and s.longitud
    ])
    sedes_list = list(sedes)
    if sedes_list:
        progreso_sedes = round(sum(s.porcentaje_checklist for s in sedes_list) / len(sedes_list))
        sedes_completadas = sum(1 for s in sedes_list if s.estado == 'completado')
    else:
        progreso_sedes = 0
        sedes_completadas = 0

    context = {
        'project': project,
        'equipo_proyecto': equipo_proyecto,
        'empleados_disponibles': empleados_disponibles,
        'insumos_proyecto': insumos_proyecto,
        'total_insumos': total_insumos,
        'costo_personal': costo_personal,
        'ingresos': ingresos,
        'rentabilidad': rentabilidad,
        'margen': margen,
        'margen_clamped': margen_clamped,
        'pagos_cliente': pagos_cliente,
        'total_pagado_cliente': total_pagado_cliente,
        'saldo_cliente': saldo_cliente,
        'sedes': sedes,
        'sedes_geo_json': sedes_geo_json,
        'progreso_sedes': progreso_sedes,
        'sedes_completadas': sedes_completadas,
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
def project_delete(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        project.delete()
        return redirect('projects')


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def create_project(request):
    if request.method == 'GET':
        return render(request, 'create_project.html', {'form': ProjectForm()})

    post_data = request.POST.copy()
    post_data.setdefault('estado_proyecto', 'pendiente')
    form = ProjectForm(post_data, request.FILES)
    if form.is_valid():
        project = form.save(commit=False)
        project.creado_por = request.user
        project.save()
        messages.success(request, f'Proyecto "{project.nombre}" creado correctamente.')
        return redirect('project_view', id_project=project.id)

    return render(request, 'create_project.html', {'form': form})




@login_required
@cargo_required(*ROLES_ADMIN_SEC)
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
@cargo_required(*ROLES_ADMIN_SEC)
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
@cargo_required(*ROLES_ADMIN)
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

    # ── Filtros de período ─────────────────────────────────────────────────────
    MESES_NOMBRES = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ]
    try:
        filtro_anio = int(request.GET.get('anio', '')) or None
    except ValueError:
        filtro_anio = None
    try:
        _mes = int(request.GET.get('mes', ''))
        filtro_mes = _mes if filtro_anio and 1 <= _mes <= 12 else None
    except ValueError:
        filtro_mes = None

    anios_disponibles = sorted(set(
        Proyecto.objects.filter(activo=True).values_list('created__year', flat=True)
    ), reverse=True)
    meses_lista = [{'num': i, 'nombre': MESES_NOMBRES[i]} for i in range(1, 13)]

    # ── Proyectos ──────────────────────────────────────────────────────────────
    proyectos_qs = Proyecto.objects.filter(activo=True)
    if filtro_anio:
        proyectos_qs = proyectos_qs.filter(created__year=filtro_anio)
        if filtro_mes:
            proyectos_qs = proyectos_qs.filter(created__month=filtro_mes)

    total_proyectos = proyectos_qs.count()
    pendientes      = proyectos_qs.filter(estado_proyecto='pendiente').count()
    en_progreso     = proyectos_qs.filter(estado_proyecto='en_progreso').count()
    completados     = proyectos_qs.filter(estado_proyecto='completado').count()

    # ── Finanzas ───────────────────────────────────────────────────────────────
    total_facturado = proyectos_qs.aggregate(total=Sum('monto_total'))['total'] or 0
    pagos_qs = PagoProyecto.objects.filter(activo=True, estado='pagado')
    if filtro_anio:
        pagos_qs = pagos_qs.filter(fecha__year=filtro_anio)
        if filtro_mes:
            pagos_qs = pagos_qs.filter(fecha__month=filtro_mes)
    total_cobrado   = pagos_qs.aggregate(total=Sum('monto'))['total'] or 0
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

    # ── Plazos basados en fecha_fin_contrato del Proyecto ──────────────────────
    hoy = timezone.now().date()
    en_30_dias = hoy + timedelta(days=30)

    proyectos_con_plazo = proyectos_qs.filter(
        estado_proyecto__in=['pendiente', 'en_progreso'],
        fecha_fin_contrato__isnull=False,
    )

    proyectos_vencidos = list(
        proyectos_con_plazo.filter(fecha_fin_contrato__lt=hoy).order_by('fecha_fin_contrato')
    )
    cnt_vencidos  = len(proyectos_vencidos)
    cnt_con_multa = sum(1 for p in proyectos_vencidos if p.estado_multa != 'normal')

    # ── Alertas clasificadas por categoría ────────────────────────────────────
    vencidos_hoy     = []
    vencidos_semana  = []
    vencidos_antiguo = []

    for p in proyectos_vencidos:
        dias = (hoy - p.fecha_fin_contrato).days
        entrada = {
            'nombre': p.nombre,
            'fecha': p.fecha_fin_contrato.strftime('%d/%m/%Y'),
            'estado': p.get_estado_proyecto_display(),
            'url': f'/proyectos/{p.id}/ver/',
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

    # Categoría 4: Alertas de empleados — jornadas pendientes de aprobación + jornadas sin pago
    alertas_empleados = []

    # 4a. Jornadas pendientes de aprobación
    jornadas_pendientes_count = (
        JornadaEmpleado.objects
        .filter(activo=True, estado='pendiente')
        .count()
    )
    if jornadas_pendientes_count > 0:
        alertas_empleados.append({
            'tipo': 'info',
            'icono': 'bi-hourglass',
            'msg': f'{jornadas_pendientes_count} jornada(s) esperan aprobación.',
            'url': '/empleados/',
        })

    # 4b. Jornadas aprobadas sin pago asignado
    empleados_deuda = (
        JornadaEmpleado.objects
        .filter(activo=True, estado='aprobada', pago__isnull=True)
        .select_related('contrato__empleado')
        .order_by('contrato__empleado__nombre')
        .values_list(
            'contrato__empleado_id',
            'contrato__empleado__nombre',
            'contrato__empleado__apellido_paterno',
        )
        .distinct()
    )
    for emp_id, nombre, apellido in empleados_deuda:
        alertas_empleados.append({
            'tipo': 'warning',
            'icono': 'bi-person-exclamation',
            'msg': f'{nombre} {apellido} tiene jornadas aprobadas pendientes de pago.',
            'url': '/pagos-empleados/',
        })

    # Categoría 5: Garantías próximas a vencer
    alertas_garantias = []
    for p in Proyecto.objects.filter(activo=True, estado_proyecto='completado', garantia_meses__gt=0):
        estado_g = p.garantia_estado
        if estado_g == 'por_vencer':
            venc = p.garantia_fecha_vencimiento
            dias_r = (venc - hoy).days if venc else 0
            alertas_garantias.append({
                'tipo': 'warning',
                'icono': 'bi-shield-exclamation',
                'msg': f'Garantía de "{p.nombre}" vence en {dias_r} día(s) ({venc.strftime("%d/%m/%Y")}).',
                'url': f'/proyectos/{p.id}/ver/',
            })

    # Categoría 6: Próximos a vencer (plazo contrato)
    proximos_hoy    = []
    proximos_semana = []
    proximos_mes    = []

    for p in proyectos_con_plazo.filter(
        fecha_fin_contrato__gte=hoy,
        fecha_fin_contrato__lte=en_30_dias,
    ).order_by('fecha_fin_contrato'):
        dias_restantes = (p.fecha_fin_contrato - hoy).days
        entrada = {
            'icono': 'bi-hourglass-split',
            'nombre': p.nombre,
            'fecha': p.fecha_fin_contrato.strftime('%d/%m/%Y'),
            'estado': p.get_estado_proyecto_display(),
            'url': f'/proyectos/{p.id}/ver/',
            'dias': dias_restantes,
        }
        if dias_restantes <= 1:
            proximos_hoy.append(entrada)
        elif dias_restantes <= 7:
            proximos_semana.append(entrada)
        else:
            proximos_mes.append(entrada)

    alertas_proximos = proximos_hoy + proximos_semana + proximos_mes

    total_alertas = len(alertas_plazos) + len(alertas_proximos) + len(alertas_cobros) + len(alertas_inventario) + len(alertas_empleados) + len(alertas_garantias)

    # ── Últimos 5 proyectos ────────────────────────────────────────────────────
    ultimos_proyectos = proyectos_qs.select_related('cliente').order_by('-created')[:5]

    # ── Datos para Chart.js ───────────────────────────────────────────────────
    import json
    tipos_labels = ['Instalación Nueva', 'Ampliación', 'Mant. Externo', 'Emergencia']
    tipos_values = [
        proyectos_qs.filter(tipo_proyecto='instalacion_nueva').count(),
        proyectos_qs.filter(tipo_proyecto='ampliacion').count(),
        proyectos_qs.filter(tipo_proyecto='mantenimiento_externo').count(),
        proyectos_qs.filter(tipo_proyecto='emergencia').count(),
    ]

    # ── Etiqueta del período activo ────────────────────────────────────────────
    if filtro_anio and filtro_mes:
        periodo_label = f'{MESES_NOMBRES[filtro_mes]} {filtro_anio}'
    elif filtro_anio:
        periodo_label = str(filtro_anio)
    else:
        periodo_label = None

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
        'alertas_garantias':    alertas_garantias,
        'total_alertas':        total_alertas,
        'cnt_vencidos':              cnt_vencidos,
        'cnt_con_multa':             cnt_con_multa,
        'jornadas_pendientes_count': jornadas_pendientes_count,
        'ultimos_proyectos':         ultimos_proyectos,
        'tipos_labels':         json.dumps(tipos_labels),
        'tipos_values':         json.dumps(tipos_values),
        'filtro_anio':          filtro_anio,
        'filtro_mes':           filtro_mes,
        'anios_disponibles':    anios_disponibles,
        'meses_lista':          meses_lista,
        'periodo_label':        periodo_label,
    }
    return render(request, 'home.html', context)


# ===================== CONTRATOS =====================

@login_required
@cargo_required(*ROLES_ADMIN)
def equipo_add(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        empleado_id = request.POST.get('empleado_id')
        empleado = get_object_or_404(Empleado, pk=empleado_id, is_active=True)
        project.equipo.add(empleado)
        messages.success(request, f'{empleado.nombre} {empleado.apellido_paterno} agregado al equipo.')
        tiene_contrato = empleado.contratos_empleado.filter(activo=True).exists()
        if not tiene_contrato:
            messages.warning(
                request,
                f'⚠ {empleado.nombre} {empleado.apellido_paterno} no tiene contrato activo. '
                f'Sus tareas completadas no generarán jornadas hasta que se le asigne un contrato.'
            )
    return redirect('project_view', id_project=project.id)



@login_required
@cargo_required(*ROLES_ADMIN)
def equipo_remove(request, id_project, id_employee):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        empleado = get_object_or_404(Empleado, pk=id_employee)
        project.equipo.remove(empleado)
        messages.success(request, f'{empleado.nombre} {empleado.apellido_paterno} removido del equipo.')
    return redirect('project_view', id_project=project.id)


# ══════════════════════════════════════════════════════════════════════════════
#  SEDES DE INSTALACIÓN
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@cargo_required(*ROLES_ADMIN)
def sede_create(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'GET':
        return render(request, 'sede_form.html', {'form': SedeForm(), 'project': project, 'accion': 'Crear'})
    form = SedeForm(request.POST)
    if form.is_valid():
        sede = form.save(commit=False)
        sede.proyecto = project
        sede.save()
        messages.success(request, f'Sede "{sede.nombre}" creada correctamente.')
        return redirect('project_view', id_project=project.id)
    return render(request, 'sede_form.html', {'form': form, 'project': project, 'accion': 'Crear'})


@login_required
def sede_view(request, id_sede):
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)

    tareas = (
        sede.tareas.filter(activo=True)
        .order_by('orden', 'created')
        .select_related('completado_por')
        .prefetch_related('participantes')
    )

    tarea_form = TareaChecklistForm()

    # Actividad del día: tareas completadas hoy en esta sede, agrupadas por empleado
    today = timezone.localdate()
    actividad_raw = (
        TareaChecklist.objects.filter(
            sede=sede, activo=True, completado=True,
            fecha_completado__date=today,
        )
        .select_related('completado_por')
        .order_by('completado_por_id', 'fecha_completado')
    )
    # Agrupar por empleado
    actividad_hoy = {}
    for t in actividad_raw:
        emp = t.completado_por
        if emp not in actividad_hoy:
            actividad_hoy[emp] = []
        actividad_hoy[emp].append(t)

    import json as _json
    equipo_json = _json.dumps([
        {'id': e.id, 'nombre': e.get_full_name(), 'cargo': e.get_cargo_display()}
        for e in sede.proyecto.equipo.filter(is_active=True).order_by('apellido_paterno')
    ])
    # Mapa tarea_id → lista de ids de participantes (para restaurar estado en el template)
    participantes_map = {
        t.id: list(t.participantes.values_list('id', flat=True))
        for t in tareas
    }

    context = {
        'sede': sede,
        'project': sede.proyecto,
        'tareas': tareas,
        'tarea_form': tarea_form,
        'actividad_hoy': actividad_hoy,
        'equipo_json': equipo_json,
        'participantes_map_json': _json.dumps(participantes_map),
    }
    return render(request, 'sede_view.html', context)


@login_required
@cargo_required(*ROLES_ADMIN)
def sede_detail(request, id_sede):
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    project = sede.proyecto
    if request.method == 'GET':
        return render(request, 'sede_form.html', {'form': SedeForm(instance=sede), 'project': project, 'sede': sede, 'accion': 'Editar'})
    form = SedeForm(request.POST, instance=sede)
    if form.is_valid():
        form.save()
        messages.success(request, f'Sede "{sede.nombre}" actualizada.')
        return redirect('sede_view', id_sede=sede.id)
    return render(request, 'sede_form.html', {'form': form, 'project': project, 'sede': sede, 'accion': 'Editar'})


@login_required
@cargo_required(*ROLES_ADMIN)
def sede_deactivate(request, id_sede):
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    id_project = sede.proyecto.id
    if request.method == 'POST':
        sede.activo = False
        sede.deleted_at = timezone.now()
        sede.deleted_by = request.user
        sede.save()
        messages.success(request, f'Sede "{sede.nombre}" eliminada.')
    return redirect('project_view', id_project=id_project)


# ══════════════════════════════════════════════════════════════════════════════
#  CHECKLIST DE TAREAS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@cargo_required(*ROLES_ADMIN)
def tarea_create(request, id_sede):
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    if request.method == 'POST':
        form = TareaChecklistForm(request.POST)
        if form.is_valid():
            tarea = form.save(commit=False)
            tarea.sede = sede
            ultimo_orden = sede.tareas.filter(activo=True).aggregate(m=db_Max('orden'))['m'] or 0
            tarea.orden = ultimo_orden + 1
            tarea.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'id': tarea.id,
                    'descripcion': tarea.descripcion,
                    'orden': tarea.orden,
                })
    return redirect('sede_view', id_sede=sede.id)


@login_required
@cargo_required('administrador', 'gerente', 'tecnico_soporte', 'instalador')
def tarea_toggle(request, id_tarea):
    """AJAX: marca/desmarca una tarea como completada."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    tarea = get_object_or_404(TareaChecklist, pk=id_tarea, activo=True)
    tarea.completado = not tarea.completado
    if tarea.completado:
        tarea.fecha_completado = timezone.now()
        tarea.completado_por = request.user
        tarea.save()
        # Auto-añadir al que marcó como participante
        tarea.participantes.set([request.user])
        # Devolver el equipo del proyecto para el modal de participantes
        equipo = [
            {'id': e.id, 'nombre': e.get_full_name(), 'cargo': e.get_cargo_display()}
            for e in tarea.sede.proyecto.equipo.filter(is_active=True).order_by('apellido_paterno')
        ]
    else:
        fecha_jornada = tarea.fecha_completado.date()
        proyecto      = tarea.sede.proyecto
        desc          = tarea.descripcion

        for empleado in list(tarea.participantes.all()):
            # Condición 3: si tiene otras tareas completadas ese día en el proyecto, no borrar
            otras = TareaChecklist.objects.filter(
                sede__proyecto=proyecto,
                completado=True,
                fecha_completado__date=fecha_jornada,
                activo=True,
            ).filter(
                Q(participantes=empleado) | Q(completado_por=empleado)
            ).exclude(pk=tarea.pk).exists()
            if otras:
                continue

            # Buscar contrato igual que la auto-creación
            contrato = (
                empleado.contratos_empleado
                .filter(fecha_inicio__lte=fecha_jornada, fecha_fin__gte=fecha_jornada)
                .order_by('-created').first()
                or empleado.contratos_empleado.order_by('-created').first()
            )
            if not contrato:
                continue

            # Condiciones 1 y 2: pendiente + observacion de auto-creación
            for j in JornadaEmpleado.objects.filter(
                contrato=contrato,
                proyecto=proyecto,
                fecha=fecha_jornada,
                estado='pendiente',
                observacion__startswith=f'Tarea completada: {desc}',
                activo=True,
            ):
                # Limpiar pago pendiente asociado
                if j.pago_id and j.pago.estado == 'pendiente':
                    pago = j.pago
                    otras_j = pago.jornadas_cubiertas.filter(activo=True).exclude(pk=j.pk).count()
                    if otras_j == 0:
                        pago.activo = False
                        pago.save()
                    else:
                        pago.monto = max(0, pago.monto - j.monto)
                        pago.save()
                j.activo     = False
                j.deleted_at = timezone.now()
                j.deleted_by = request.user
                j.save()

        tarea.fecha_completado = None
        tarea.completado_por   = None
        tarea.save()
        tarea.participantes.clear()
        equipo = []
    tarea.sede._sync_estado()
    pct_sede = tarea.sede.porcentaje_checklist

    nombre_usuario = tarea.completado_por.get_full_name() if tarea.completado_por else ''
    fecha_str = tarea.fecha_completado.strftime('%d/%m/%Y %H:%M') if tarea.fecha_completado else ''

    return JsonResponse({
        'ok': True,
        'completado': tarea.completado,
        'porcentaje': pct_sede,
        'estado_sede': tarea.sede.estado,
        'completado_por': nombre_usuario,
        'fecha_completado': fecha_str,
        'usuario_id': request.user.id,
        'equipo': equipo,
    })


@login_required
@cargo_required(*ROLES_CAMPO)
def tarea_set_participantes(request, id_tarea):
    """AJAX: guarda los participantes de una tarea completada y auto-crea jornadas pendientes."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    tarea = get_object_or_404(TareaChecklist, pk=id_tarea, activo=True, completado=True)
    import json as _json
    try:
        body = _json.loads(request.body)
        ids = body.get('participantes', [])
    except (ValueError, KeyError):
        ids = []
    # Siempre incluir al que marcó la tarea
    if tarea.completado_por_id and tarea.completado_por_id not in ids:
        ids.append(tarea.completado_por_id)
    # Validar que todos pertenezcan al equipo del proyecto
    equipo_ids = set(tarea.sede.proyecto.equipo.values_list('id', flat=True))
    ids_validos = [i for i in ids if i in equipo_ids]
    tarea.participantes.set(ids_validos)

    # Auto-crear jornada pendiente para cada participante si no tiene una ese día
    proyecto = tarea.sede.proyecto
    fecha_jornada = tarea.fecha_completado.date()
    participantes_qs = Empleado.objects.filter(pk__in=ids_validos)
    jornadas_creadas = []
    sin_contrato = []
    for empleado in participantes_qs:
        # Primero intentar el contrato que cubre la fecha exacta
        contrato = empleado.contratos_empleado.filter(
            fecha_inicio__lte=fecha_jornada,
            fecha_fin__gte=fecha_jornada,
        ).order_by('-created').first()
        # Si no hay ninguno vigente, usar el más reciente (activo o no)
        if not contrato:
            contrato = empleado.contratos_empleado.order_by('-created').first()
        if not contrato:
            sin_contrato.append(empleado.get_full_name())
            continue
        ya_existe = JornadaEmpleado.objects.filter(
            contrato=contrato, proyecto=proyecto, fecha=fecha_jornada, activo=True,
        ).exists()
        if ya_existe:
            continue
        JornadaEmpleado.objects.create(
            contrato=contrato,
            proyecto=proyecto,
            fecha=fecha_jornada,
            dias=1.0,
            estado='pendiente',
            observacion=f'Tarea completada: {tarea.descripcion}',
            registrado_por=request.user,
        )
        jornadas_creadas.append(empleado.get_full_name())

    nombres = [
        tarea.sede.proyecto.equipo.get(pk=i).get_full_name()
        for i in ids_validos
    ]
    return JsonResponse({
        'ok': True,
        'participantes': nombres,
        'jornadas_creadas': jornadas_creadas,
        'sin_contrato': sin_contrato,
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def tarea_delete(request, id_tarea):
    tarea = get_object_or_404(TareaChecklist, pk=id_tarea, activo=True)
    id_sede = tarea.sede.id
    if request.method == 'POST':
        tarea.activo = False
        tarea.save()
        tarea.sede._sync_estado()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
    return redirect('sede_view', id_sede=id_sede)


@login_required
@cargo_required(*ROLES_ADMIN)
def tareas_reorder(request, id_sede):
    """AJAX: recibe lista ordenada de IDs y actualiza el campo `orden` de cada tarea."""
    import json
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        ids = json.loads(request.body).get('ids', [])
    except (ValueError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    tareas = {t.id: t for t in sede.tareas.filter(activo=True)}
    for posicion, tarea_id in enumerate(ids, start=1):
        tarea = tareas.get(int(tarea_id))
        if tarea:
            tarea.orden = posicion
            tarea.save(update_fields=['orden'])
    return JsonResponse({'ok': True})


@login_required
@cargo_required(*ROLES_ADMIN)
def tarea_edit(request, id_tarea):
    """AJAX: actualiza la descripción de una tarea existente."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    tarea = get_object_or_404(TareaChecklist, pk=id_tarea, activo=True)
    descripcion = request.POST.get('descripcion', '').strip()
    if not descripcion:
        return JsonResponse({'ok': False, 'error': 'La descripción no puede estar vacía.'}, status=400)
    tarea.descripcion = descripcion
    tarea.save(update_fields=['descripcion'])
    return JsonResponse({'ok': True, 'descripcion': tarea.descripcion})


# ══════════════════════════════════════════════════════════════════════════════
#  QR POR INSUMO INSTALADO
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def qr_insumo(request, id_requiere):
    """Devuelve imagen PNG del QR que apunta al detalle del insumo asignado."""
    from inventario.models import Requiere as RequiereModel
    import qrcode
    from io import BytesIO

    req = get_object_or_404(RequiereModel, pk=id_requiere)
    url = request.build_absolute_uri(f'/insumos-proyecto/{req.id}/')
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return HttpResponse(buf, content_type='image/png')


# ── Pagos del cliente ─────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def payment_list(request):
    proyecto_id        = request.GET.get('proyecto_id', '')
    filter_tipo        = request.GET.get('filter_tipo', '')
    filter_estado_pago = request.GET.get('filter_estado_pago', '')
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

    payments = (
        PagoProyecto.objects.filter(activo=True)
        .select_related('proyecto')
        .order_by('-fecha')
    )
    if proyecto_id:
        payments = payments.filter(proyecto_id=proyecto_id)
    if filter_tipo:
        payments = payments.filter(tipo_pago=filter_tipo)
    if filter_estado_pago:
        payments = payments.filter(proyecto__estado_pago=filter_estado_pago)

    total_payments = payments.count()
    pagos_confirmados = payments.filter(estado='pagado')
    total_monto_filtro = pagos_confirmados.aggregate(t=Sum('monto'), td=Sum('descuento'))
    total_cobrado_filtro = float(total_monto_filtro['t'] or 0) + float(total_monto_filtro['td'] or 0)
    total_pendiente_monto = float(payments.filter(estado='pendiente').aggregate(t=Sum('monto'))['t'] or 0)

    paginator = Paginator(payments, per_page)
    try:
        payments_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        payments_page = paginator.page(1)

    proyectos_lista = Proyecto.objects.filter(activo=True).order_by('codigo').values('id', 'codigo', 'nombre')

    # Proyectos completados con saldo pendiente (alerta global)
    completados_sin_pagar = (
        Proyecto.objects.filter(activo=True, estado_proyecto='completado')
        .exclude(estado_pago='pagado').count()
    )

    # Batch: cobrado total (solo pagos confirmados) + monto ref por proyecto (página actual)
    proj_ids = list({p.proyecto_id for p in payments_page})
    cobrado_batch = {
        pb['proyecto_id']: float(pb['total'] or 0) + float(pb['total_desc'] or 0)
        for pb in PagoProyecto.objects.filter(activo=True, estado='pagado', proyecto_id__in=proj_ids)
            .values('proyecto_id')
            .annotate(total=Sum('monto'), total_desc=Sum('descuento'))
    }
    monto_base = {
        p['id']: float(p['monto_total'])
        for p in Proyecto.objects.filter(pk__in=proj_ids).values('id', 'monto_total')
    }
    for p in payments_page:
        monto_ref = monto_base.get(p.proyecto_id, 0)
        cobrado   = cobrado_batch.get(p.proyecto_id, 0)
        p.saldo_proyecto    = round(monto_ref - cobrado, 2)
        p.cobrado_proyecto  = round(cobrado, 2)
        p.monto_ref_proyecto = round(monto_ref, 2)

    return render(request, 'payments.html', {
        'payments':              payments_page,
        'total_payments':        total_payments,
        'total_cobrado_filtro':  total_cobrado_filtro,
        'total_pendiente_monto': total_pendiente_monto,
        'completados_sin_pagar': completados_sin_pagar,
        'proyecto_id':           proyecto_id,
        'filter_tipo':           filter_tipo,
        'filter_estado_pago':    filter_estado_pago,
        'per_page':              per_page,
        'proyectos_lista':       proyectos_lista,
    })


def _proyectos_pago_data():
    proyectos = Proyecto.objects.filter(activo=True).prefetch_related('pagos')
    data = {}
    for p in proyectos:
        totals = p.pagos.filter(activo=True, estado='pagado').aggregate(
            total_monto=Sum('monto'),
            total_descuento=Sum('descuento'),
        )
        pagado     = float(totals['total_monto'] or 0)
        descuentos = float(totals['total_descuento'] or 0)
        cubierto   = pagado + descuentos
        monto_ref  = float(p.monto_acordado or p.monto_total)
        saldo      = monto_ref - cubierto

        data[str(p.id)] = {
            'monto_total':    monto_ref,
            'tiene_contrato': bool(p.monto_acordado),
            'pagado':         pagado,
            'descuentos':     descuentos,
            'cubierto':       cubierto,
            'saldo':          saldo,
            'multa_sugerida': float(p.multa_acumulada),
            'multa_estado':   p.estado_multa,
            'multa_tope':     p.multa_tope_alcanzado,
            'dias_retraso':   p.dias_retraso,
        }
    return data


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def create_payment(request):
    proyectos_data = json.dumps(_proyectos_pago_data())
    if request.method == 'GET':
        return render(request, 'create_payment.html', {'form': PaymentForm(), 'proyectos_data': proyectos_data})
    form = PaymentForm(request.POST)
    if form.is_valid():
        payment = form.save()
        messages.success(request, f'El pago de Bs. {payment.monto} fue registrado exitosamente.')
        return redirect('payments')
    return render(request, 'create_payment.html', {'form': form, 'proyectos_data': proyectos_data, 'error': 'Por favor, proporcione datos válidos'})


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def payment_detail(request, id_payment):
    payment = get_object_or_404(PagoProyecto, pk=id_payment, activo=True)

    # Balance del proyecto excluyendo el pago actual
    proyecto = payment.proyecto
    otros = PagoProyecto.objects.filter(proyecto=proyecto, activo=True).exclude(pk=payment.pk)
    otros_agg = otros.aggregate(tm=Sum('monto'), td=Sum('descuento'))
    otros_cubiertos = float(otros_agg['tm'] or 0) + float(otros_agg['td'] or 0)
    cubierto_total  = otros_cubiertos + float(payment.monto) + float(payment.descuento or 0)
    monto_ref = float(proyecto.monto_acordado or proyecto.monto_total)
    balance = {
        'monto_ref':      monto_ref,
        'tiene_contrato': bool(proyecto.monto_acordado),
        'cubierto':       cubierto_total,
        'saldo':          monto_ref - cubierto_total,
    }

    if request.method == 'GET':
        return render(request, 'payment_detail.html', {
            'payment': payment,
            'form': PaymentForm(instance=payment, edit_mode=True),
            'balance': balance,
        })
    form = PaymentForm(request.POST, instance=payment, edit_mode=True)
    if form.is_valid():
        form.save()
        messages.success(request, f"El pago del proyecto '{payment.proyecto.nombre}' fue actualizado exitosamente.")
        return redirect('payments')
    return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'balance': balance, 'error': 'Error al actualizar el pago'})


@login_required
def payment_view(request, id_payment):
    payment = get_object_or_404(PagoProyecto, pk=id_payment, activo=True)
    proyecto = payment.proyecto
    otros = PagoProyecto.objects.filter(proyecto=proyecto, activo=True).exclude(pk=payment.pk)
    otros_agg = otros.aggregate(tm=Sum('monto'), td=Sum('descuento'))
    otros_cubiertos = float(otros_agg['tm'] or 0) + float(otros_agg['td'] or 0)
    cubierto_total  = otros_cubiertos + float(payment.monto) + float(payment.descuento or 0)
    monto_ref = float(proyecto.monto_acordado or proyecto.monto_total)
    balance = {
        'monto_ref':      monto_ref,
        'tiene_contrato': bool(proyecto.monto_acordado),
        'cubierto':       cubierto_total,
        'saldo':          monto_ref - cubierto_total,
    }
    return render(request, 'payment_view.html', {'payment': payment, 'balance': balance})


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_payment(request, id_payment):
    payment = get_object_or_404(PagoProyecto, id=id_payment, activo=True)
    if request.method == 'POST':
        payment.activo = False
        payment.deleted_at = timezone.now()
        payment.deleted_by = request.user
        payment.save()
        messages.success(request, f"El pago de Bs. {payment.monto} del proyecto '{payment.proyecto.nombre}' ha sido inhabilitado.")
    return redirect('payments')


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def confirmar_pago_proyecto(request, id_payment):
    payment = get_object_or_404(PagoProyecto, pk=id_payment, activo=True, estado='pendiente')
    if request.method == 'POST':
        fecha     = request.POST.get('fecha', '').strip()
        tipo_pago = request.POST.get('tipo_pago', 'efectivo').strip()
        num_ref   = request.POST.get('numero_referencia', '').strip()
        if not fecha:
            messages.error(request, 'La fecha de pago es obligatoria.')
            return render(request, 'confirmar_pago_proyecto.html', {'payment': payment})
        payment.fecha             = fecha
        payment.tipo_pago         = tipo_pago
        payment.numero_referencia = num_ref
        payment.estado            = 'pagado'
        payment.save()
        messages.success(request, f'Pago de Bs. {payment.monto} confirmado para "{payment.proyecto.nombre}".')
        return redirect('payments')
    return render(request, 'confirmar_pago_proyecto.html', {'payment': payment})


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def filter_payments_by_project_name(request):
    project_name = request.GET.get('project_name', '')
    start_date   = request.GET.get('start_date', '')
    end_date     = request.GET.get('end_date', '')
    filter_tipo  = request.GET.get('filter_tipo', '')
    per_page = int(request.GET.get('per_page', 10))
    if per_page not in (10, 20, 50, 100):
        per_page = 10
    page = request.GET.get('page', 1)

    projects = Proyecto.objects.filter(activo=True).values('nombre').distinct()
    payments = PagoProyecto.objects.filter(activo=True).select_related('proyecto', 'proyecto__cliente')

    if project_name:
        payments = payments.filter(proyecto__nombre__icontains=project_name)
    if start_date:
        payments = payments.filter(fecha__gte=start_date)
    if end_date:
        payments = payments.filter(fecha__lte=end_date)
    if filter_tipo:
        payments = payments.filter(tipo_pago=filter_tipo)

    total_monto         = payments.aggregate(total=Sum('monto'))['total'] or 0
    monto_efectivo      = payments.filter(tipo_pago='efectivo').aggregate(total=Sum('monto'))['total'] or 0
    monto_transferencia = payments.filter(tipo_pago='transferencia').aggregate(total=Sum('monto'))['total'] or 0
    count_efectivo      = payments.filter(tipo_pago='efectivo').count()
    count_transferencia = payments.filter(tipo_pago='transferencia').count()
    total_payments      = payments.count()

    # PDF/Excel: lista completa; HTML: paginada
    payments = payments.order_by('-fecha')
    if 'pdf' in request.GET or 'excel' in request.GET:
        payments_page = None
    else:
        paginator = Paginator(payments, per_page)
        try:
            payments_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            payments_page = paginator.page(1)
        payments = list(payments_page.object_list)

    context = {
        'payments': payments,
        'projects': projects,
        'project_name': project_name,
        'start_date': start_date,
        'end_date': end_date,
        'filter_tipo': filter_tipo,
        'total_monto': total_monto,
        'monto_efectivo': monto_efectivo,
        'monto_transferencia': monto_transferencia,
        'count_efectivo': count_efectivo,
        'count_transferencia': count_transferencia,
        'total_payments': total_payments,
        'payments_page': payments_page,
        'per_page': per_page,
        'now': timezone.now(),
        'generado_por': request.user.get_full_name() or request.user.username,
    }

    if 'pdf' in request.GET:
        template = get_template('payments_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="reporte_pagos.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    if 'excel' in request.GET:
        NUM_COLS = 7
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Pagos Clientes'
        title_fill   = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        title_font   = Font(bold=True, size=14, color='D4B84A')
        info_fill    = PatternFill(start_color='1B4D90', end_color='1B4D90', fill_type='solid')
        info_font    = Font(size=9, color='FFFFFF')
        header_fill  = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        header_font  = Font(bold=True, color='D4B84A', size=10)
        alt_fill     = PatternFill(start_color='EFF2F8', end_color='EFF2F8', fill_type='solid')
        total_fill   = PatternFill(start_color='E8EDF5', end_color='E8EDF5', fill_type='solid')
        total_font   = Font(bold=True, size=10, color='0F2D5A')
        center       = Alignment(horizontal='center', vertical='center')
        left         = Alignment(horizontal='left',   vertical='center')
        right_al     = Alignment(horizontal='right',  vertical='center')
        cell_border  = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='thin', color='C0C8D8'),  bottom=Side(style='thin', color='C0C8D8'),
        )
        total_border = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='medium', color='0F2D5A'), bottom=Side(style='medium', color='0F2D5A'),
        )
        money_fmt = '#,##0.00'
        ws.append(['Reporte de Pagos de Clientes — SOBOTEC S.R.L.'])
        ws.merge_cells(f'A1:{openpyxl.utils.get_column_letter(NUM_COLS)}1')
        ws['A1'].font = title_font; ws['A1'].fill = title_fill
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 26
        gen_por  = request.user.get_full_name() or request.user.username
        info_str = f'Generado por: {gen_por}  |  Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        if project_name: info_str += f'  |  Proyecto: {project_name}'
        if start_date:   info_str += f'  |  Desde: {start_date}'
        if end_date:     info_str += f'  |  Hasta: {end_date}'
        if filter_tipo:  info_str += f'  |  Tipo: {filter_tipo}'
        ws.append([info_str])
        ws.merge_cells(f'A2:{openpyxl.utils.get_column_letter(NUM_COLS)}2')
        ws['A2'].font = info_font; ws['A2'].fill = info_fill
        ws['A2'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[2].height = 18
        ws.append([]); ws.row_dimensions[3].height = 6
        headers = ['Proyecto', 'Cliente', 'Estado Proyecto', 'Monto Total Proy. (Bs.)',
                   'Monto Pago (Bs.)', 'Fecha', 'Tipo de Pago']
        ws.append(headers)
        for cell in ws[4]:
            cell.font = header_font; cell.fill = header_fill
            cell.alignment = center; cell.border = cell_border
        ws.row_dimensions[4].height = 22
        last_row = 4
        for i, p in enumerate(payments, start=5):
            cliente_str = (f'{p.proyecto.cliente.nombre} {p.proyecto.cliente.apellido_paterno}'
                           if p.proyecto.cliente else '—')
            ws.append([
                p.proyecto.nombre, cliente_str,
                p.proyecto.get_estado_proyecto_display(),
                float(p.proyecto.monto_total), float(p.monto),
                p.fecha.strftime('%d/%m/%Y') if p.fecha else '—',
                p.get_tipo_pago_display(),
            ])
            row_fill = alt_fill if i % 2 == 0 else None
            for j, cell in enumerate(ws[i], start=1):
                if row_fill: cell.fill = row_fill
                cell.border = cell_border
                if j in (4, 5):
                    cell.alignment = right_al; cell.number_format = money_fmt
                elif j == 6: cell.alignment = center
                else:        cell.alignment = left
            ws.row_dimensions[i].height = 16
            last_row = i
        total_row = last_row + 1
        ws.append(['', 'TOTAL', '', '', float(total_monto), '', ''])
        for j, cell in enumerate(ws[total_row], start=1):
            cell.font = total_font; cell.fill = total_fill; cell.border = total_border
            if j in (4, 5): cell.alignment = right_al; cell.number_format = money_fmt
            else:            cell.alignment = left
        ws.row_dimensions[total_row].height = 18
        for col_idx, width in enumerate([30, 25, 16, 20, 18, 12, 16], start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width
        ws.freeze_panes = 'A5'
        ws.auto_filter.ref = f'A4:{openpyxl.utils.get_column_letter(NUM_COLS)}4'
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="reporte_pagos.xlsx"'
        wb.save(response)
        return response

    return render(request, 'payments_by_project_name.html', context)


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def payment_analysis(request):
    start_date = request.GET.get('start_date')
    end_date   = request.GET.get('end_date')
    payments   = PagoProyecto.objects.filter(activo=True)
    if start_date:
        try:
            payments = payments.filter(fecha__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    if end_date:
        try:
            payments = payments.filter(fecha__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    payment_type_counts = payments.values('tipo_pago').annotate(count=Count('tipo_pago'))
    type_labels = [t['tipo_pago'] for t in payment_type_counts]
    type_values = [t['count'] for t in payment_type_counts]
    _pay_colors = ['#1B4D90', '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51', '#e76f51']
    fig, ax = plt.subplots(figsize=(5, 5.5), facecolor='white')
    fig.subplots_adjust(top=0.95, bottom=0.14)
    if type_values:
        wedges_p, _, autotexts_p = ax.pie(
            type_values, autopct='%1.1f%%', startangle=90,
            colors=_pay_colors[:len(type_values)],
            wedgeprops={'linewidth': 2.5, 'edgecolor': 'white', 'width': 0.65},
            pctdistance=0.75,
        )
        for t in autotexts_p:
            t.set_fontsize(11)
            t.set_fontweight('bold')
        centre_p = plt.Circle((0, 0), 0.35, fc='white')
        ax.add_patch(centre_p)
        ax.legend(wedges_p, type_labels, loc='lower center',
                  bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=10,
                  frameon=False, handlelength=1.2)
    else:
        ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                transform=ax.transAxes, fontsize=12, color='#888888')
    ax.axis('equal')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=200)
    buf.seek(0)
    graphic = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    totals = payments.aggregate(
        total_monto=Sum('monto'),
        total_descuento=Sum('descuento'),
    )
    total_monto     = (totals['total_monto']     or 0) + (totals['total_descuento'] or 0)
    total_efectivo  = payments.filter(tipo_pago='efectivo').aggregate(t=Sum('monto'))['t'] or 0
    total_transfer  = payments.filter(tipo_pago='transferencia').aggregate(t=Sum('monto'))['t'] or 0
    return render(request, 'payment_analysis.html', {
        'graphic': graphic,
        'payment_type_counts': payment_type_counts,
        'start_date': start_date,
        'end_date': end_date,
        'message': None if payments.exists() else 'No hay pagos en este rango de fechas.',
        'total_pagos': payments.count(),
        'total_monto': total_monto,
        'total_efectivo': total_efectivo,
        'total_transfer': total_transfer,
    })








# ── Vista de Seguimiento de Avance ────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN)
def seguimiento_avance(request):
    from empleados.models import Empleado as EmpleadoModel
    from collections import defaultdict

    filter_estado   = request.GET.get('estado', '')
    search_nombre   = request.GET.get('q', '').strip()
    filter_empleado = request.GET.get('empleado', '')

    # Prefetch anidado: sedes activas → tareas activas (evita N+1 y los 2 count() de porcentaje_checklist)
    tareas_prefetch = Prefetch(
        'tareas',
        queryset=TareaChecklist.objects.filter(activo=True),
        to_attr='tareas_activas',
    )
    sedes_prefetch = Prefetch(
        'sedes',
        queryset=Sede.objects.filter(activo=True).prefetch_related(tareas_prefetch),
        to_attr='sedes_activas',
    )

    todos = list(
        Proyecto.objects
        .filter(activo=True)
        .select_related('cliente')
        .prefetch_related(sedes_prefetch, 'equipo')
        .order_by('estado_proyecto', 'nombre')
    )

    def _progreso_sede(sede):
        total = len(sede.tareas_activas)
        if total == 0:
            return 0
        completadas = sum(1 for t in sede.tareas_activas if t.completado)
        return round(completadas / total * 100)

    def _progreso_proyecto(sedes):
        if not sedes:
            return 0
        return round(sum(_progreso_sede(s) for s in sedes) / len(sedes))

    def _build_entry(proyecto):
        sedes = proyecto.sedes_activas
        return {
            'proyecto':          proyecto,
            'progreso':          _progreso_proyecto(sedes),
            'total_sedes':       len(sedes),
            'sedes_completadas': sum(1 for s in sedes if s.estado == 'completado'),
        }

    todos_avance = [_build_entry(p) for p in todos]

    # ── KPIs globales ────────────────────────────────────────────────────────
    total_proyectos       = len(todos_avance)
    proyectos_completados = sum(1 for p in todos_avance if p['proyecto'].estado_proyecto == 'completado')
    proyectos_en_progreso = sum(1 for p in todos_avance if p['proyecto'].estado_proyecto == 'en_progreso')
    promedio_avance = (
        round(sum(p['progreso'] for p in todos_avance) / total_proyectos)
        if total_proyectos > 0 else 0
    )

    # ── Filtrado para la tabla (Python, datos ya cargados) ───────────────────
    proyectos_avance = todos_avance
    if filter_estado:
        proyectos_avance = [p for p in proyectos_avance if p['proyecto'].estado_proyecto == filter_estado]
    if search_nombre:
        proyectos_avance = [p for p in proyectos_avance if search_nombre.lower() in p['proyecto'].nombre.lower()]

    # ── Instaladores y técnicos ──────────────────────────────────────────────
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count

    today           = timezone.localdate()
    week_start      = today - timedelta(days=today.weekday())       # lunes de esta semana
    last_week_start = week_start - timedelta(weeks=1)
    month_start     = today.replace(day=1)

    emp_a_proyectos = defaultdict(list)
    for entry in todos_avance:
        for emp in entry['proyecto'].equipo.all():
            emp_a_proyectos[emp.id].append(entry)

    empleados_campo = list(
        EmpleadoModel.objects
        .filter(is_active=True, cargo__in=['instalador', 'tecnico_soporte'])
        .order_by('apellido_paterno', 'nombre')
    )
    emp_ids = [e.id for e in empleados_campo]

    def _tareas_por_emp(fecha_gte, fecha_lt=None):
        qs = TareaChecklist.objects.filter(
            activo=True, completado=True,
            completado_por_id__in=emp_ids,
            fecha_completado__date__gte=fecha_gte,
        )
        if fecha_lt:
            qs = qs.filter(fecha_completado__date__lt=fecha_lt)
        return {
            r['completado_por_id']: r['t']
            for r in qs.values('completado_por_id').annotate(t=Count('id'))
        }

    esta_semana_map   = _tareas_por_emp(week_start)
    semana_pasada_map = _tareas_por_emp(last_week_start, week_start)
    este_mes_map      = _tareas_por_emp(month_start)

    empleados_avance = []
    for emp in empleados_campo:
        entradas = emp_a_proyectos.get(emp.id, [])
        t_semana     = esta_semana_map.get(emp.id, 0)
        t_sem_ant    = semana_pasada_map.get(emp.id, 0)
        t_mes        = este_mes_map.get(emp.id, 0)
        proy_activos = sum(1 for e in entradas if e['proyecto'].estado_proyecto == 'en_progreso')
        if not entradas and t_mes == 0:
            continue
        progresos = [e['progreso'] for e in entradas]
        empleados_avance.append({
            'empleado':          emp,
            'porcentaje':        round(sum(progresos) / len(progresos)) if progresos else 0,
            'detalle_proyectos': [{'proyecto': e['proyecto'], 'progreso': e['progreso']} for e in entradas],
            'proy_activos':      proy_activos,
            't_semana':          t_semana,
            't_sem_ant':         t_sem_ant,
            't_mes':             t_mes,
            # tendencia: +1 sube, 0 igual, -1 baja
            'tendencia':         1 if t_semana > t_sem_ant else (-1 if t_semana < t_sem_ant else 0),
        })

    # Ordenar por tareas esta semana desc, luego mes desc
    empleados_avance.sort(key=lambda x: (-x['t_semana'], -x['t_mes']))

    if filter_empleado:
        try:
            filter_empleado = int(filter_empleado)
            empleados_avance = [e for e in empleados_avance if e['empleado'].id == filter_empleado]
        except ValueError:
            filter_empleado = ''

    context = {
        'proyectos_avance':      proyectos_avance,
        'empleados_avance':      empleados_avance,
        'empleados_campo':       empleados_campo,
        'total_proyectos':       total_proyectos,
        'proyectos_completados': proyectos_completados,
        'proyectos_en_progreso': proyectos_en_progreso,
        'promedio_avance':       promedio_avance,
        'filter_estado':         filter_estado,
        'search_nombre':         search_nombre,
        'filter_empleado':       filter_empleado,
        'week_start':            week_start,
        'last_week_start':       last_week_start,
        'month_start':           month_start,
        'today':                 today,
    }
    return render(request, 'seguimiento.html', context)


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def analisis_financiero(request):
    """
    Vista global de análisis financiero: compara presupuesto vs costo real
    (insumos + mano de obra) y muestra rentabilidad por proyecto.
    """
    from django.db.models import Sum, Prefetch
    from empleados.models import ContratoEmpleado

    proyecto_id   = request.GET.get('proyecto_id', '').strip()
    filter_estado = request.GET.get('estado', '')
    fecha_desde   = request.GET.get('fecha_desde', '').strip()
    fecha_hasta   = request.GET.get('fecha_hasta', '').strip()
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 20
    except (ValueError, TypeError):
        per_page = 20
    page = request.GET.get('page', 1)
    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    proyectos_qs = (
        Proyecto.objects
        .filter(activo=True)
        .select_related('cliente')
        .prefetch_related(
            Prefetch('insumos', queryset=Requiere.objects.filter(activo=True).select_related('insumo').prefetch_related('lotes__compra')),
        )
        .order_by('-created')
    )
    if proyecto_id:
        proyectos_qs = proyectos_qs.filter(pk=proyecto_id)
    if filter_estado:
        proyectos_qs = proyectos_qs.filter(estado_proyecto=filter_estado)
    if fecha_desde:
        try:
            proyectos_qs = proyectos_qs.filter(created__date__gte=fecha_desde)
        except (ValueError, TypeError):
            fecha_desde = ''
    if fecha_hasta:
        try:
            proyectos_qs = proyectos_qs.filter(created__date__lte=fecha_hasta)
        except (ValueError, TypeError):
            fecha_hasta = ''

    proyectos_lista = Proyecto.objects.filter(activo=True).order_by('codigo').values('id', 'codigo', 'nombre')

    # Costo de personal: suma directa desde JornadaEmpleado aprobadas × monto_diario (calculado en DB).
    # Incluye todos los empleados que alguna vez trabajaron, aunque ya no estén en el equipo.
    costo_personal_agg = (
        JornadaEmpleado.objects
        .filter(activo=True, estado='aprobada')
        .values('proyecto_id')
        .annotate(
            costo=Sum(
                ExpressionWrapper(
                    F('dias') * F('contrato__monto_acordado') / F('contrato__dias_laborales'),
                    output_field=ModelDecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
    )
    costo_personal_map = {j['proyecto_id']: j['costo'] or 0 for j in costo_personal_agg}

    # Batch de pagos por proyecto
    pagos_agg = (
        PagoProyecto.objects
        .filter(activo=True)
        .values('proyecto_id')
        .annotate(total=Sum('monto'), total_desc=Sum('descuento'))
    )
    pagos_map = {p['proyecto_id']: (p['total'] or 0) + (p['total_desc'] or 0) for p in pagos_agg}

    all_filas = []
    totales = {'presupuesto': 0, 'costo_insumos': 0, 'costo_insumos_garantia': 0, 'costo_personal': 0, 'cobrado': 0}

    for p in proyectos_qs:
        costo_insumos          = sum(r.costo_total for r in p.insumos.all())
        costo_insumos_garantia = sum(r.costo_total for r in p.insumos.all() if r.durante_garantia)
        costo_personal         = costo_personal_map.get(p.pk, 0)
        cobrado                = pagos_map.get(p.pk, 0)
        costo_total            = costo_insumos + costo_personal
        rentabilidad           = p.monto_total - costo_total
        margen                 = round((rentabilidad / p.monto_total * 100), 1) if p.monto_total else 0

        totales['presupuesto']            += p.monto_total
        totales['costo_insumos']          += costo_insumos
        totales['costo_insumos_garantia'] += costo_insumos_garantia
        totales['costo_personal']         += costo_personal
        totales['cobrado']                += cobrado

        all_filas.append({
            'proyecto':               p,
            'costo_insumos':          costo_insumos,
            'costo_insumos_garantia': costo_insumos_garantia,
            'costo_personal':         costo_personal,
            'costo_total':            costo_total,
            'cobrado':                cobrado,
            'saldo':                  p.monto_total - cobrado,
            'rentabilidad':           rentabilidad,
            'margen':                 margen,
        })

    totales['costo_total']  = totales['costo_insumos'] + totales['costo_personal']
    totales['rentabilidad'] = totales['presupuesto'] - totales['costo_total']
    totales['margen']       = round(
        (totales['rentabilidad'] / totales['presupuesto'] * 100), 1
    ) if totales['presupuesto'] else 0

    paginator   = Paginator(all_filas, per_page)
    filas_page  = paginator.get_page(page)

    return render(request, 'analisis_financiero.html', {
        'filas':           list(filas_page),
        'filas_page':      filas_page,
        'totales':         totales,
        'proyecto_id':     proyecto_id,
        'filter_estado':   filter_estado,
        'fecha_desde':     fecha_desde,
        'fecha_hasta':     fecha_hasta,
        'per_page':        per_page,
        'proyectos_lista': proyectos_lista,
    })
