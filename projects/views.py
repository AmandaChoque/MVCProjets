from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError

from .form import ProjectForm, ClienteForm, ProgresoForm, ContratoProyectoForm, SedeForm, FotoSedeForm, TareaChecklistForm, PaymentForm, PlantillaTareaForm, ItemPlantillaForm, GrupoTareaForm
from .models import Proyecto, Cliente, Progreso, HistorialPresupuesto, Sede, FotoSede, TareaChecklist, Notificacion, Pago, PlantillaTarea, ItemPlantilla, GrupoTarea
from empleados.models import Empleado, ContratoEmpleado, ContratoProyecto, JornadaEmpleado, PagoEmpleado
from inventario.models import Insumo, Requiere
from django.contrib.auth.decorators import login_required
from .decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC, ROLES_CAMPO

from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.db.models import Q, Count, Sum, OuterRef, Subquery, F, Max as db_Max, Prefetch
from django.db import models
from django.db.models.functions import TruncMonth
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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

    context = {
        'graphic': graphic,
        'total_completados': total_completados,
        'total_en_progreso': total_en_progreso,
        'total_pendientes': total_pendientes,
        'total_proyectos': total_completados + total_en_progreso + total_pendientes,
    }
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
    instalacion_count            = tipo_counts.get('instalacion_nueva', 0)
    ampliacion_count             = tipo_counts.get('ampliacion', 0)
    mantenimiento_garantia_count = tipo_counts.get('mantenimiento_garantia', 0)
    mantenimiento_externo_count  = tipo_counts.get('mantenimiento_externo', 0)
    mantenimiento_count          = mantenimiento_garantia_count + mantenimiento_externo_count
    emergencia_count             = tipo_counts.get('emergencia', 0)

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
        'mantenimiento_garantia_count': mantenimiento_garantia_count,
        'mantenimiento_externo_count': mantenimiento_externo_count,
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

    contrato_fecha_inicio_qs = ContratoProyecto.objects.filter(
        proyecto=OuterRef('pk'), activo=True
    ).order_by('-fecha_inicio').values('fecha_inicio')[:1]

    contrato_fecha_fin_qs = ContratoProyecto.objects.filter(
        proyecto=OuterRef('pk'), activo=True
    ).order_by('-fecha_inicio').values('fecha_fin')[:1]

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

    # Pre-compute saldo, avance y cumplimiento por proyecto
    projects_list = list(projects)
    for p in projects_list:
        p.monto_saldo = p.monto_total - (p.monto_cobrado or 0)
        sedes_list_p = p.sedes_activas
        if sedes_list_p:
            p.ultimo_avance = round(sum(s.porcentaje_checklist for s in sedes_list_p) / len(sedes_list_p))
        else:
            p.ultimo_avance = 0
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

    paginator = Paginator(qs, per_page)
    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

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
    contrato_proyecto = project.contratos.filter(activo=True).first()
    insumos_proyecto = project.insumos.select_related('insumo').order_by('-created')
    total_insumos = sum(r.costo_total for r in insumos_proyecto)

    # ── Equipo del proyecto (M2M) con estadísticas de jornadas ────────────────
    # Prefetch contratos activos para evitar N+1 (una query en vez de N)
    miembros = project.equipo.filter(is_active=True).prefetch_related(
        Prefetch(
            'contratos_empleado',
            queryset=ContratoEmpleado.objects.filter(activo=True),
            to_attr='_contratos_activos',
        )
    )

    # Batch: total de días y última fecha por empleado en una sola query
    jornadas_agg = (
        JornadaEmpleado.objects
        .filter(proyecto=project, activo=True)
        .values('contrato__empleado_id')
        .annotate(total_dias=Sum('dias'), ultima_fecha=db_Max('fecha'))
    )
    jornadas_map = {j['contrato__empleado_id']: j for j in jornadas_agg}

    equipo_proyecto = []
    costo_personal = 0
    for emp in miembros:
        j = jornadas_map.get(emp.pk, {})
        total_dias = j.get('total_dias') or 0
        contrato_emp = emp._contratos_activos[0] if emp._contratos_activos else None
        costo = total_dias * contrato_emp.monto_diario if contrato_emp else 0
        costo_personal += costo
        equipo_proyecto.append({
            'empleado': emp,
            'total_dias': total_dias,
            'costo': costo,
            'ultima_fecha': j.get('ultima_fecha'),
        })
    # Empleados disponibles para agregar (activos y que no están ya en el equipo)
    empleados_disponibles = Empleado.objects.filter(is_active=True).exclude(
        pk__in=miembros.values_list('pk', flat=True)
    ).order_by('apellido_paterno')

    # ── Historial de cambios de monto ──────────────────────────────────────────
    historial_monto = HistorialPresupuesto.objects.filter(proyecto=project).order_by('-fecha_modificacion')

    # ── Rentabilidad ───────────────────────────────────────────────────────────
    ingresos = project.monto_total
    rentabilidad = ingresos - total_insumos - costo_personal
    margen = round((rentabilidad / ingresos * 100), 1) if ingresos > 0 else 0
    margen_clamped = max(0, min(100, margen))

    # ── Pagos del cliente al proyecto ──────────────────────────────────────────
    pagos_cliente = project.pagos.filter(activo=True).order_by('fecha')
    total_pagado_cliente = pagos_cliente.aggregate(total=Sum('monto'))['total'] or 0
    saldo_cliente = ingresos - total_pagado_cliente

    # ── Sedes del proyecto ────────────────────────────────────────────────────
    sedes = project.sedes.filter(activo=True).prefetch_related('tareas', 'fotos', 'insumos', 'grupos')

    # ── Indicador de ritmo (grupos completados vs esperado) ───────────────────
    hace_7_dias = timezone.now() - timedelta(days=7)
    grupos_completados_semana = GrupoTarea.objects.filter(
        sede__proyecto=project,
        activo=True,
        fecha_completado__gte=hace_7_dias,
    ).count()
    ritmo_esperado = project.ritmo_semanal
    if grupos_completados_semana >= ritmo_esperado:
        ritmo_estado = 'ok'
    elif grupos_completados_semana >= ritmo_esperado * 0.75:
        ritmo_estado = 'alerta'
    else:
        ritmo_estado = 'atrasado'
    sedes_geo_json = json.dumps([
        {
            'lat': float(s.latitud), 'lng': float(s.longitud),
            'nombre': s.nombre, 'direccion': s.direccion,
            'estado': s.estado,
            'url': f'/sedes/{s.id}/ver/',
        }
        for s in sedes if s.latitud and s.longitud
    ])

    # Progreso general basado en sedes: promedio de porcentaje_checklist
    sedes_list = list(sedes)
    if sedes_list:
        progreso_sedes = round(sum(s.porcentaje_checklist for s in sedes_list) / len(sedes_list))
        sedes_completadas = sum(1 for s in sedes_list if s.estado == 'completado')
    else:
        progreso_sedes = 0
        sedes_completadas = 0

    context = {
        'project': project,
        'progresos': progresos,
        'porcentaje_actual': porcentaje_actual,
        'equipo_proyecto': equipo_proyecto,
        'empleados_disponibles': empleados_disponibles,
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
        'sedes': sedes,
        'sedes_geo_json': sedes_geo_json,
        'progreso_sedes': progreso_sedes,
        'sedes_completadas': sedes_completadas,
        'grupos_completados_semana': grupos_completados_semana,
        'ritmo_esperado': ritmo_esperado,
        'ritmo_estado': ritmo_estado,
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
        if not project.contratos.filter(activo=True).exists():
            messages.error(request, 'No se puede completar el proyecto sin un contrato de proyecto activo.')
            return redirect('project_view', id_project=project.id)
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

    if form.is_valid() and contrato_form.is_valid():
        project = form.save(commit=False)
        project.creado_por = request.user
        project.save()

        contrato = contrato_form.save(commit=False)
        contrato.proyecto = project
        contrato.save()
        project.monto_total = contrato.monto_acordado
        project.save(update_fields=['monto_total'])

        messages.success(request, f'Proyecto "{project.nombre}" creado correctamente.')
        return redirect('project_view', id_project=project.id)

    return render(request, 'create_project.html', {
        'form': form,
        'contrato_form': contrato_form,
    })




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
    pagos_qs = Pago.objects.filter(activo=True)
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

    # ── Plazos basados en ContratoProyecto.fecha_fin (el plazo real acordado) ──
    # Nota: Proyecto.fecha_fin se asigna automáticamente al completar (no es el plazo)
    hoy = timezone.now().date()
    en_30_dias = hoy + timedelta(days=30)

    contratos_proyecto_qs = ContratoProyecto.objects.filter(
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
    contratos_completados = ContratoEmpleado.objects.filter(
        activo=True,
        jornadas__proyecto__estado_proyecto='completado',
        jornadas__activo=True,
    ).select_related('empleado').annotate(
        total_pagado=Subquery(pagado_subq)
    ).distinct()
    for contrato in contratos_completados:
        pagado = contrato.total_pagado or 0
        if pagado < contrato.monto_acordado:
            pendiente = contrato.monto_acordado - pagado
            alertas_empleados.append({
                'tipo': 'warning',
                'icono': 'bi-person-exclamation',
                'msg': f'{contrato.empleado.nombre} {contrato.empleado.apellido_paterno} tiene Bs. {pendiente:.2f} pendientes.',
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
    tipos_labels = ['Instalación Nueva', 'Ampliación', 'Mant. Garantía', 'Mant. Externo', 'Emergencia']
    tipos_values = [
        proyectos_qs.filter(tipo_proyecto='instalacion_nueva').count(),
        proyectos_qs.filter(tipo_proyecto='ampliacion').count(),
        proyectos_qs.filter(tipo_proyecto='mantenimiento_garantia').count(),
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
        'total_alertas':        total_alertas,
        'cnt_vencidos':         cnt_vencidos,
        'ultimos_proyectos':    ultimos_proyectos,
        'tipos_labels':         tipos_labels,
        'tipos_values':         tipos_values,
        'filtro_anio':          filtro_anio,
        'filtro_mes':           filtro_mes,
        'anios_disponibles':    anios_disponibles,
        'meses_lista':          meses_lista,
        'periodo_label':        periodo_label,
    }
    return render(request, 'home.html', context)


# ===================== PROGRESO =====================

def _puede_registrar_progreso(user, proyecto):
    """Admins/gerentes siempre pueden. Otros solo si tienen contrato activo en el proyecto."""
    if user.is_superuser:
        return True
    cargo = getattr(user, 'cargo', None)
    if cargo in ROLES_ADMIN:
        return True
    return JornadaEmpleado.objects.filter(
        contrato__empleado=user, proyecto=proyecto, activo=True
    ).exists()


@login_required
def create_progreso(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if not _puede_registrar_progreso(request.user, project):
        messages.error(request, 'Solo puedes registrar progreso en proyectos donde tienes un contrato activo.')
        return redirect('project_view', id_project=project.id)
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
                if not project.contratos.filter(activo=True).exists():
                    messages.warning(request, 'Progreso registrado, pero el proyecto no puede iniciar sin un contrato de proyecto activo.')
                    return redirect('project_view', id_project=project.id)
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
    if not _puede_registrar_progreso(request.user, project):
        messages.error(request, 'Solo puedes editar progreso en proyectos donde tienes un contrato activo.')
        return redirect('project_view', id_project=project.id)
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
@cargo_required(*ROLES_ADMIN)
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
@cargo_required(*ROLES_ADMIN)
def equipo_add(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if request.method == 'POST':
        empleado_id = request.POST.get('empleado_id')
        empleado = get_object_or_404(Empleado, pk=empleado_id, is_active=True)
        project.equipo.add(empleado)
        messages.success(request, f'{empleado.nombre} {empleado.apellido_paterno} agregado al equipo.')
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


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def create_contrato_proyecto(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    # Check if project already has an active contract
    existing = project.contratos.filter(activo=True).first()
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
            contrato.proyecto = project
            contrato.save()
            project.monto_total = contrato.monto_acordado
            project._current_user = request.user
            project.save(update_fields=['monto_total'])
            messages.success(request, 'Contrato del proyecto registrado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_contrato_proyecto.html', {'form': form, 'project': project})


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def contrato_proyecto_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoProyecto, pk=id_contrato, activo=True)
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
@cargo_required(*ROLES_ADMIN)
def deactivate_contrato_proyecto(request, id_contrato):
    contrato = get_object_or_404(ContratoProyecto, pk=id_contrato, activo=True)
    if request.method == 'POST':
        contrato.activo = False
        contrato.deleted_at = timezone.now()
        contrato.deleted_by = request.user
        contrato.save()
        messages.success(request, 'Contrato del proyecto inhabilitado.')
    return redirect('project_view', id_project=contrato.proyecto.id)


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
    insumos_sede = sede.insumos.filter(activo=True).select_related('insumo')

    # Grupos con sus tareas pre-cargadas
    grupos = list(
        sede.grupos.filter(activo=True).prefetch_related(
            Prefetch(
                'tareas',
                queryset=TareaChecklist.objects.filter(activo=True)
                    .order_by('orden', 'created')
                    .select_related('completado_por'),
            )
        )
    )

    # Tareas sin grupo asignado
    tareas_sin_grupo = sede.tareas.filter(activo=True, grupo__isnull=True).order_by('orden', 'created').select_related('completado_por')

    fotos = sede.fotos.filter(activo=True)
    plantillas = PlantillaTarea.objects.filter(activo=True).order_by('tipo', 'nombre')
    foto_form = FotoSedeForm()
    tarea_form = TareaChecklistForm()
    grupo_form = GrupoTareaForm()

    # Actividad del día: tareas completadas hoy en esta sede, agrupadas por empleado
    today = timezone.localdate()
    actividad_raw = (
        TareaChecklist.objects.filter(
            sede=sede, activo=True, completado=True,
            fecha_completado__date=today,
        )
        .select_related('completado_por', 'grupo')
        .order_by('completado_por_id', 'fecha_completado')
    )
    # Agrupar por empleado
    actividad_hoy = {}
    for t in actividad_raw:
        emp = t.completado_por
        if emp not in actividad_hoy:
            actividad_hoy[emp] = []
        actividad_hoy[emp].append(t)

    context = {
        'sede': sede,
        'project': sede.proyecto,
        'insumos_sede': insumos_sede,
        'grupos': grupos,
        'tareas_sin_grupo': tareas_sin_grupo,
        'fotos': fotos,
        'foto_form': foto_form,
        'tarea_form': tarea_form,
        'grupo_form': grupo_form,
        'plantillas': plantillas,
        'actividad_hoy': actividad_hoy,
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
            grupo_id = request.POST.get('grupo_id')
            if grupo_id:
                try:
                    tarea.grupo = GrupoTarea.objects.get(pk=grupo_id, sede=sede, activo=True)
                except GrupoTarea.DoesNotExist:
                    pass
            ultimo_orden = sede.tareas.filter(activo=True).aggregate(m=db_Max('orden'))['m'] or 0
            tarea.orden = ultimo_orden + 1
            tarea.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'id': tarea.id,
                    'descripcion': tarea.descripcion,
                    'orden': tarea.orden,
                    'grupo_id': tarea.grupo_id,
                })
    return redirect('sede_view', id_sede=sede.id)


@login_required
@cargo_required(*ROLES_CAMPO)
def tarea_toggle(request, id_tarea):
    """AJAX: marca/desmarca una tarea como completada."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    tarea = get_object_or_404(TareaChecklist, pk=id_tarea, activo=True)
    tarea.completado = not tarea.completado
    if tarea.completado:
        tarea.fecha_completado = timezone.now()
        tarea.completado_por = request.user
    else:
        tarea.fecha_completado = None
        tarea.completado_por = None
    tarea.save()
    tarea.sede._sync_estado()
    pct_sede = tarea.sede.porcentaje_checklist

    # Info del grupo (si tiene)
    grupo_info = None
    if tarea.grupo_id:
        tarea.grupo.refresh_from_db()
        grupo_info = {
            'id': tarea.grupo_id,
            'porcentaje': tarea.grupo.porcentaje,
            'completado': tarea.grupo.completado,
        }

    nombre_usuario = tarea.completado_por.get_full_name() or tarea.completado_por.username if tarea.completado_por else ''
    fecha_str = tarea.fecha_completado.strftime('%d/%m/%Y %H:%M') if tarea.fecha_completado else ''

    return JsonResponse({
        'ok': True,
        'completado': tarea.completado,
        'porcentaje': pct_sede,
        'estado_sede': tarea.sede.estado,
        'grupo': grupo_info,
        'completado_por': nombre_usuario,
        'fecha_completado': fecha_str,
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
def grupo_create(request, id_sede):
    """AJAX: crea un nuevo GrupoTarea dentro de una sede."""
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    if request.method == 'POST':
        form = GrupoTareaForm(request.POST)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.sede = sede
            ultimo = sede.grupos.filter(activo=True).aggregate(m=db_Max('orden'))['m'] or 0
            grupo.orden = ultimo + 1
            grupo.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'id': grupo.id,
                    'nombre': grupo.nombre,
                    'tipo': grupo.get_tipo_display(),
                    'tipo_key': grupo.tipo,
                    'orden': grupo.orden,
                })
        elif request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    return redirect('sede_view', id_sede=sede.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def grupo_delete(request, id_grupo):
    """AJAX: desactiva (soft-delete) un GrupoTarea."""
    grupo = get_object_or_404(GrupoTarea, pk=id_grupo, activo=True)
    id_sede = grupo.sede.id
    if request.method == 'POST':
        grupo.activo = False
        grupo.deleted_at = timezone.now()
        grupo.deleted_by = request.user
        grupo.save()
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


@login_required
@cargo_required(*ROLES_ADMIN)
def aplicar_plantilla_sede(request, id_sede):
    """AJAX: aplica los items de una plantilla a una sede ya existente (agrega las tareas faltantes)."""
    import json as _json
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    try:
        id_plantilla = _json.loads(request.body).get('id_plantilla')
    except (ValueError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
    plantilla = get_object_or_404(PlantillaTarea, pk=id_plantilla, activo=True)
    items = plantilla.items.filter(activo=True).order_by('orden')
    ultimo_orden = sede.tareas.filter(activo=True).aggregate(m=db_Max('orden'))['m'] or 0
    nuevas = []
    for i, item in enumerate(items, start=1):
        tarea = TareaChecklist.objects.create(
            sede=sede,
            descripcion=item.descripcion,
            orden=ultimo_orden + i,
        )
        nuevas.append({'id': tarea.id, 'descripcion': tarea.descripcion, 'orden': tarea.orden})
    return JsonResponse({'ok': True, 'tareas': nuevas, 'count': len(nuevas)})


# ══════════════════════════════════════════════════════════════════════════════
#  FOTOS DE SEDE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@cargo_required(*ROLES_CAMPO)
def foto_upload(request, id_sede):
    sede = get_object_or_404(Sede, pk=id_sede, activo=True)
    if request.method == 'POST':
        form = FotoSedeForm(request.POST, request.FILES)
        if form.is_valid():
            foto = form.save(commit=False)
            foto.sede = sede
            foto.subida_por = request.user
            foto.save()
            messages.success(request, 'Foto subida correctamente.')
        else:
            messages.error(request, 'Error al subir la foto. Verifica el formato.')
    return redirect('sede_view', id_sede=sede.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def foto_delete(request, id_foto):
    foto = get_object_or_404(FotoSede, pk=id_foto, activo=True)
    id_sede = foto.sede.id
    if request.method == 'POST':
        foto.activo = False
        foto.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
    return redirect('sede_view', id_sede=id_sede)


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


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICACIONES
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def notificaciones_list(request):
    notifs = request.user.notificaciones.order_by('-fecha')
    no_leidas = notifs.filter(leida=False).count()
    return render(request, 'notificaciones.html', {
        'notificaciones': notifs,
        'no_leidas': no_leidas,
    })


@login_required
def notificacion_marcar_leida(request, id_notif):
    if request.method == 'POST':
        notif = get_object_or_404(Notificacion, pk=id_notif, destinatario=request.user)
        notif.leida = True
        notif.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            pendientes = request.user.notificaciones.filter(leida=False).count()
            return JsonResponse({'ok': True, 'pendientes': pendientes})
    return redirect('notificaciones_list')


@login_required
def notificaciones_marcar_todas(request):
    if request.method == 'POST':
        request.user.notificaciones.filter(leida=False).update(leida=True)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
    return redirect('notificaciones_list')


# ── Pagos del cliente ─────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def payment_list(request):
    search_proyecto = request.GET.get('search_proyecto', '')
    filter_tipo     = request.GET.get('filter_tipo', '')
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

    payments = Pago.objects.filter(activo=True).select_related('proyecto').order_by('-fecha')
    if search_proyecto:
        payments = payments.filter(proyecto__nombre__icontains=search_proyecto)
    if filter_tipo:
        payments = payments.filter(tipo_pago=filter_tipo)

    total_payments = payments.count()
    paginator = Paginator(payments, per_page)
    try:
        payments_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        payments_page = paginator.page(1)

    return render(request, 'payments.html', {
        'payments': payments_page,
        'total_payments': total_payments,
        'search_proyecto': search_proyecto,
        'filter_tipo': filter_tipo,
        'per_page': per_page,
    })


def _proyectos_pago_data():
    from empleados.models import ContratoProyecto
    proyectos = Proyecto.objects.filter(activo=True).prefetch_related('pagos')
    contratos = {c.proyecto_id: c for c in ContratoProyecto.objects.filter(activo=True).select_related('proyecto')}
    data = {}
    for p in proyectos:
        totals = p.pagos.filter(activo=True).aggregate(
            total_monto=Sum('monto'),
            total_descuento=Sum('descuento'),
        )
        pagado     = float(totals['total_monto'] or 0)
        descuentos = float(totals['total_descuento'] or 0)
        cubierto   = pagado + descuentos
        saldo      = float(p.monto_total) - cubierto

        contrato = contratos.get(p.id)
        multa_sugerida  = float(contrato.multa_acumulada) if contrato else 0
        multa_estado    = contrato.estado_multa if contrato else 'normal'
        multa_tope      = bool(contrato.multa_tope_alcanzado) if contrato else False
        dias_retraso    = contrato.dias_retraso if contrato else 0

        data[str(p.id)] = {
            'monto_total':     float(p.monto_total),
            'pagado':          pagado,
            'descuentos':      descuentos,
            'cubierto':        cubierto,
            'saldo':           saldo,
            'multa_sugerida':  multa_sugerida,
            'multa_estado':    multa_estado,
            'multa_tope':      multa_tope,
            'dias_retraso':    dias_retraso,
        }
    return data


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def create_payment(request):
    proyectos_data = _proyectos_pago_data()
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
    payment = get_object_or_404(Pago, pk=id_payment, activo=True)
    if request.method == 'GET':
        return render(request, 'payment_detail.html', {
            'payment': payment,
            'form': PaymentForm(instance=payment, edit_mode=True),
        })
    form = PaymentForm(request.POST, instance=payment, edit_mode=True)
    if form.is_valid():
        form.save()
        messages.success(request, f"El pago del proyecto '{payment.proyecto.nombre}' fue actualizado exitosamente.")
        return redirect('payments')
    return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'error': 'Error al actualizar el pago'})


@login_required
def payment_view(request, id_payment):
    payment = get_object_or_404(Pago, pk=id_payment, activo=True)
    return render(request, 'payment_view.html', {'payment': payment})


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def deactivate_payment(request, id_payment):
    payment = get_object_or_404(Pago, id=id_payment, activo=True)
    if request.method == 'POST':
        payment.activo = False
        payment.deleted_at = timezone.now()
        payment.deleted_by = request.user
        payment.save()
        messages.success(request, f"El pago de Bs. {payment.monto} del proyecto '{payment.proyecto.nombre}' ha sido inhabilitado.")
    return redirect('payments')


@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def filter_payments_by_project_name(request):
    project_name = request.GET.get('project_name', '')
    start_date   = request.GET.get('start_date', '')
    end_date     = request.GET.get('end_date', '')
    filter_tipo  = request.GET.get('filter_tipo', '')

    projects = Proyecto.objects.filter(activo=True).values('nombre').distinct()
    payments = Pago.objects.filter(activo=True).select_related('proyecto', 'proyecto__cliente')

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
    payments   = Pago.objects.filter(activo=True)
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
    fig, ax = plt.subplots()
    ax.pie(type_values, labels=type_labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
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


# ══════════════════════════════════════════════════════════════════════════════
#  PLANTILLAS DE TAREAS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@cargo_required(*ROLES_ADMIN)
def plantillas_list(request):
    plantillas = PlantillaTarea.objects.filter(activo=True).prefetch_related('items').order_by('tipo', 'nombre')
    return render(request, 'plantillas_list.html', {'plantillas': plantillas})


@login_required
@cargo_required(*ROLES_ADMIN)
def plantilla_create(request):
    if request.method == 'GET':
        return render(request, 'plantilla_form.html', {'form': PlantillaTareaForm(), 'accion': 'Crear'})
    form = PlantillaTareaForm(request.POST)
    if form.is_valid():
        plantilla = form.save()
        messages.success(request, f'Plantilla "{plantilla.nombre}" creada.')
        return redirect('plantilla_detail', id_plantilla=plantilla.id)
    return render(request, 'plantilla_form.html', {'form': form, 'accion': 'Crear'})


@login_required
@cargo_required(*ROLES_ADMIN)
def plantilla_detail(request, id_plantilla):
    plantilla = get_object_or_404(PlantillaTarea, pk=id_plantilla, activo=True)
    items     = plantilla.items.filter(activo=True).order_by('orden')
    if request.method == 'GET':
        return render(request, 'plantilla_form.html', {
            'form': PlantillaTareaForm(instance=plantilla),
            'plantilla': plantilla, 'items': items, 'item_form': ItemPlantillaForm(), 'accion': 'Editar',
        })
    form = PlantillaTareaForm(request.POST, instance=plantilla)
    if form.is_valid():
        form.save()
        messages.success(request, 'Plantilla actualizada.')
        return redirect('plantilla_detail', id_plantilla=plantilla.id)
    return render(request, 'plantilla_form.html', {
        'form': form, 'plantilla': plantilla, 'items': items, 'item_form': ItemPlantillaForm(), 'accion': 'Editar',
    })


@login_required
@cargo_required(*ROLES_ADMIN)
def plantilla_deactivate(request, id_plantilla):
    plantilla = get_object_or_404(PlantillaTarea, pk=id_plantilla, activo=True)
    if request.method == 'POST':
        plantilla.activo     = False
        plantilla.deleted_at = timezone.now()
        plantilla.deleted_by = request.user
        plantilla.save()
        messages.success(request, f'Plantilla "{plantilla.nombre}" eliminada.')
    return redirect('plantillas_list')


@login_required
@cargo_required(*ROLES_ADMIN)
def item_plantilla_create(request, id_plantilla):
    plantilla = get_object_or_404(PlantillaTarea, pk=id_plantilla, activo=True)
    if request.method == 'POST':
        form = ItemPlantillaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.plantilla = plantilla
            item.save()
            messages.success(request, 'Tarea agregada a la plantilla.')
    return redirect('plantilla_detail', id_plantilla=plantilla.id)


@login_required
@cargo_required(*ROLES_ADMIN)
def item_plantilla_edit(request, id_item):
    item = get_object_or_404(ItemPlantilla, pk=id_item, activo=True)
    id_plantilla = item.plantilla.id
    if request.method == 'POST':
        form = ItemPlantillaForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tarea actualizada.')
    return redirect('plantilla_detail', id_plantilla=id_plantilla)


@login_required
@cargo_required(*ROLES_ADMIN)
def item_plantilla_delete(request, id_item):
    item = get_object_or_404(ItemPlantilla, pk=id_item, activo=True)
    id_plantilla = item.plantilla.id
    if request.method == 'POST':
        item.activo     = False
        item.deleted_at = timezone.now()
        item.deleted_by = request.user
        item.save()
        messages.success(request, 'Tarea eliminada de la plantilla.')
    return redirect('plantilla_detail', id_plantilla=id_plantilla)


@login_required
@cargo_required(*ROLES_ADMIN)
def items_plantilla_reorder(request, id_plantilla):
    """AJAX: reordena los items de una plantilla dado un listado de IDs."""
    import json as _json
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    plantilla = get_object_or_404(PlantillaTarea, pk=id_plantilla, activo=True)
    try:
        ids = _json.loads(request.body).get('ids', [])
    except (ValueError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
    items = {i.id: i for i in plantilla.items.filter(activo=True)}
    for posicion, item_id in enumerate(ids, start=1):
        item = items.get(int(item_id))
        if item:
            item.orden = posicion
            item.save(update_fields=['orden'])
    return JsonResponse({'ok': True})
