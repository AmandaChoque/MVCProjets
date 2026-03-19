import io
import base64
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from xhtml2pdf import pisa

from projects.models import Proyecto, ContratoEmpleado
from projects.decorators import cargo_required, ROLES_ADMIN, ROLES_ADMIN_SEC
from .models import Pago, PagoEmpleado
from .forms import PaymentForm, PagoEmpleadoForm


# ── Pagos del cliente ─────────────────────────────────────────────────────────

@login_required
def payment_list(request):
    search_proyecto = request.GET.get('search_proyecto', '')
    filter_estado   = request.GET.get('filter_estado', '')
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

    payments = Pago.objects.filter(activo=True).order_by('-id')
    if search_proyecto:
        payments = payments.filter(proyecto__nombre__icontains=search_proyecto)
    if filter_estado:
        payments = payments.filter(estado=filter_estado)
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
        'filter_estado': filter_estado,
        'filter_tipo': filter_tipo,
        'per_page': per_page,
    })


def _proyectos_data():
    proyectos = Proyecto.objects.filter(activo=True).prefetch_related('pagos')
    data = {}
    for p in proyectos:
        pagado = p.pagos.filter(activo=True, estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
        data[str(p.id)] = {
            'monto_total': float(p.monto_total),
            'pagado': float(pagado),
            'saldo': float(p.monto_total - pagado),
        }
    return data

@login_required
@cargo_required(*ROLES_ADMIN_SEC)
def create_payment(request):
    proyectos_data = _proyectos_data()
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
    proyectos_data = _proyectos_data()
    if request.method == 'GET':
        return render(request, 'payment_detail.html', {
            'payment': payment,
            'form': PaymentForm(instance=payment),
            'proyectos_data': proyectos_data,
        })
    form = PaymentForm(request.POST, instance=payment)
    if form.is_valid():
        form.save()
        messages.success(request, f"El pago del proyecto '{payment.proyecto.nombre}' fue actualizado exitosamente.")
        return redirect('payments')
    return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'proyectos_data': proyectos_data, 'error': 'Error al actualizar el pago'})


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
def filter_payments_by_project_name(request):
    project_name  = request.GET.get('project_name', '')
    start_date    = request.GET.get('start_date', '')
    end_date      = request.GET.get('end_date', '')
    filter_estado = request.GET.get('filter_estado', '')
    filter_tipo   = request.GET.get('filter_tipo', '')

    projects = Proyecto.objects.values('nombre').distinct()
    payments = Pago.objects.filter(activo=True).select_related('proyecto', 'proyecto__cliente')

    if project_name:
        payments = payments.filter(proyecto__nombre__icontains=project_name)
    if start_date:
        payments = payments.filter(fecha__gte=start_date)
    if end_date:
        payments = payments.filter(fecha__lte=end_date)
    if filter_estado:
        payments = payments.filter(estado=filter_estado)
    if filter_tipo:
        payments = payments.filter(tipo_pago=filter_tipo)

    total_monto      = payments.aggregate(total=Sum('monto'))['total'] or 0
    monto_pagado     = payments.filter(estado='pagado').aggregate(total=Sum('monto'))['total'] or 0
    monto_pendiente  = payments.filter(estado='pendiente').aggregate(total=Sum('monto'))['total'] or 0
    count_pagado     = payments.filter(estado='pagado').count()
    count_pendiente  = payments.filter(estado='pendiente').count()

    context = {
        'payments': payments,
        'projects': projects,
        'project_name': project_name,
        'start_date': start_date,
        'end_date': end_date,
        'filter_estado': filter_estado,
        'filter_tipo': filter_tipo,
        'total_monto': total_monto,
        'monto_pagado': monto_pagado,
        'monto_pendiente': monto_pendiente,
        'count_pagado': count_pagado,
        'count_pendiente': count_pendiente,
        'now': timezone.now(),
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

    return render(request, 'payments_by_project_name.html', context)


@login_required
def payment_analysis(request):
    start_date = request.GET.get('start_date')
    end_date   = request.GET.get('end_date')
    payments   = Pago.objects.all()

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

    payment_status_counts = payments.values('estado').annotate(count=Count('estado'))
    payment_type_counts   = payments.values('tipo_pago').annotate(count=Count('tipo_pago'))

    status_labels = [s['estado'] for s in payment_status_counts]
    status_values = [s['count'] for s in payment_status_counts]

    fig, ax = plt.subplots()
    ax.pie(status_values, labels=status_labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graphic = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    return render(request, 'payment_analysis.html', {
        'graphic': graphic,
        'payment_status_counts': payment_status_counts,
        'payment_type_counts': payment_type_counts,
        'start_date': start_date,
        'end_date': end_date,
        'message': None if payments.exists() else 'No hay pagos en este rango de fechas.',
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
        'contrato__empleado', 'contrato__proyecto'
    ).order_by('-fecha')

    if search_empleado:
        qs = qs.filter(
            Q(contrato__empleado__nombre__icontains=search_empleado) |
            Q(contrato__empleado__apellido_paterno__icontains=search_empleado)
        )
    if search_proyecto:
        qs = qs.filter(contrato__proyecto__nombre__icontains=search_proyecto)

    paginator = Paginator(qs, per_page)
    try:
        pagos_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        pagos_page = paginator.page(1)

    total_monto = qs.aggregate(t=Sum('monto'))['t'] or 0
    contratos_activos = ContratoEmpleado.objects.filter(activo=True).select_related('empleado', 'proyecto').order_by('empleado__nombre')

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
    pagado = qs.aggregate(t=Sum('monto'))['t'] or 0
    return {
        'pagado': pagado,
        'saldo': contrato.monto_acordado - pagado,
    }

@login_required
def create_pago_empleado(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True)
    resumen  = _contrato_resumen(contrato)
    if request.method == 'GET':
        return render(request, 'create_pago_empleado.html', {
            'form': PagoEmpleadoForm(),
            'contrato': contrato,
            'resumen': resumen,
        })
    form = PagoEmpleadoForm(request.POST)
    if form.is_valid():
        pago = form.save(commit=False)
        pago.contrato = contrato
        pago.save()
        messages.success(request, f'Pago de Bs. {pago.monto} registrado para {contrato.empleado.nombre}.')
        return redirect('project_view', id_project=contrato.proyecto.id)
    return render(request, 'create_pago_empleado.html', {'form': form, 'contrato': contrato, 'resumen': resumen})


@login_required
@cargo_required(*ROLES_ADMIN)
def pago_empleado_detail(request, id_pago):
    pago     = get_object_or_404(PagoEmpleado, pk=id_pago, activo=True)
    contrato = pago.contrato
    resumen  = _contrato_resumen(contrato, excluir_pago_id=pago.id)
    if request.method == 'GET':
        return render(request, 'pago_empleado_detail.html', {
            'form': PagoEmpleadoForm(instance=pago),
            'pago': pago,
            'contrato': contrato,
            'resumen': resumen,
        })
    form = PagoEmpleadoForm(request.POST, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, 'Pago actualizado correctamente.')
        return redirect('project_view', id_project=contrato.proyecto.id)
    return render(request, 'pago_empleado_detail.html', {'form': form, 'pago': pago, 'contrato': contrato, 'resumen': resumen})


@login_required
@cargo_required(*ROLES_ADMIN)
def deactivate_pago_empleado(request, id_pago):
    pago = get_object_or_404(PagoEmpleado, pk=id_pago)
    id_project = pago.contrato.proyecto.id
    if request.method == 'POST':
        pago.activo = False
        pago.deleted_at = timezone.now()
        pago.deleted_by = request.user
        pago.save()
        messages.success(request, 'Pago eliminado correctamente.')
    return redirect('project_view', id_project=id_project)
