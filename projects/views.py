from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages

from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError

from .form import ProjectForm, EmpleadoForm, PaymentForm, PublicEntityForm, ProposalForm, ClienteForm, ProgresoForm, ContratoEmpleadoForm, ContratoProyectoForm, ProveedorForm, InsumoForm, RequerirForm, RealizarForm
from .models import Proyecto, Empleado, Pago, EntidadPublica, Propuesta, Cliente, Progreso, ContratoEmpleado, ContratoProyecto, Proveedor, Insumo, Requiere, Realizar
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.db.models import Q, Count, Sum

from django.views.generic import ListView, CreateView
from django.utils.timezone import now
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def home(request):
    return render(request, 'home.html')


def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html', {
            'form': UserCreationForm
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                    username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                return redirect('projects')
            except IntegrityError:
                return render(request, 'signup.html', {
                    'form': UserCreationForm,
                    'error': 'Username already exists'
                })
        return render(request, 'signup.html', {
            'form': UserCreationForm,
            'error': 'Password do not match'
        })


@login_required
def signout(request):
    logout(request)
    return redirect('landing')


def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html', {
            'form': AuthenticationForm
        })
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            return render(request, 'signin.html', {
                'form': AuthenticationForm,
                'error': 'Username or password is incorrect'
            })
        else:
            login(request, user)
            return redirect('dashboard')


@login_required
def extend_session(request):
    """
    View to extend the user session. Called via AJAX when user wants to extend their session.
    """
    # Update the session's expiry time
    request.session.set_expiry(1800)  # 30 minutes from now
    return JsonResponse({'status': 'success', 'message': 'Session extended'})


@login_required
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
def project_analysis(request):
    projects = Proyecto.objects.all()

    if not projects.exists():
        context = {
            'message': "No existen proyectos registrados.",
        }
        return render(request, 'project_analysis.html', context)

    project_counts = projects.values('tipo_proyecto').annotate(total=Count('tipo_proyecto'))
    licitacion_count = next((item['total'] for item in project_counts if item['tipo_proyecto'] == 'licitacion'), 0)
    contratacion_count = next((item['total'] for item in project_counts if item['tipo_proyecto'] == 'contratacion_directa'), 0)

    labels = ['Licitación', 'Contratación Directa']
    sizes = [licitacion_count, contratacion_count]
    colors = ['#66b3ff', '#99ff99']
    explode = (0.1, 0)

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png).decode('utf-8')

    context = {
        'graphic': graphic,
        'licitacion_count': licitacion_count,
        'contratacion_count': contratacion_count,
    }
    return render(request, 'project_analysis.html', context)


@login_required
def project_report(request):
    project_type = request.GET.get('project_type') or None
    project_status = request.GET.get('project_status') or None

    projects = Proyecto.objects.filter(activo=True).select_related('cliente')

    if project_type:
        projects = projects.filter(tipo_proyecto=project_type)
    if project_status:
        projects = projects.filter(estado_proyecto=project_status)

    monto_total = projects.aggregate(total=Sum('monto_total'))['total'] or 0
    count_completado = projects.filter(estado_proyecto='completado').count()
    count_en_progreso = projects.filter(estado_proyecto='en_progreso').count()
    count_pendiente = projects.filter(estado_proyecto='pendiente').count()

    context = {
        'projects': projects,
        'project_type': project_type,
        'project_status': project_status,
        'monto_total': monto_total,
        'count_completado': count_completado,
        'count_en_progreso': count_en_progreso,
        'count_pendiente': count_pendiente,
        'now': timezone.now(),
    }

    if 'pdf' in request.GET:
        template = get_template('project_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        if 'download' in request.GET:
            response['Content-Disposition'] = 'attachment; filename="reporte_proyectos.pdf"'
        else:
            response['Content-Disposition'] = 'inline; filename="reporte_proyectos.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
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
def deactivate_project(request, id_project):
    project = get_object_or_404(Proyecto, id=id_project, user=request.user)
    project.activo = False
    project.deleted_at = timezone.now()
    project.save()
    return redirect('projects')



@login_required
def project_detail(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    if request.method == 'GET':
        form = ProjectForm(instance=project)
        return render(request, 'project_detail.html', {'project': project, 'form': form})
    else:
        try:
            form = ProjectForm(request.POST, instance=project)
            form.save()
            return redirect('projects')
        except ValueError:
            return render(request, 'project_detail.html', {'project': project, 'form': form, 'error': "Error al actualizar el proyecto"})


@login_required
def project_view(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    progresos = project.progresos.all().order_by('-fecha', '-created')
    ultimo_progreso = progresos.first()
    porcentaje_actual = ultimo_progreso.porcentaje if ultimo_progreso else 0
    contratos_empleados = project.contratos_empleados.filter(activo=True).select_related('empleado')
    contrato_proyecto = getattr(project, 'contrato_proyecto', None)
    if contrato_proyecto and not contrato_proyecto.activo:
        contrato_proyecto = None
    insumos_proyecto = project.insumos.select_related('insumo').order_by('-created')
    total_insumos = sum(r.subtotal for r in insumos_proyecto)

    # ── Rentabilidad ───────────────────────────────────────────────────────────
    costo_personal = contratos_empleados.aggregate(total=Sum('monto_acordado'))['total'] or 0
    ingresos = project.monto_total
    rentabilidad = ingresos - total_insumos - costo_personal
    margen = round((rentabilidad / ingresos * 100), 1) if ingresos > 0 else 0

    return render(request, 'project_view.html', {
        'project': project,
        'progresos': progresos,
        'porcentaje_actual': porcentaje_actual,
        'contratos_empleados': contratos_empleados,
        'contrato_proyecto': contrato_proyecto,
        'insumos_proyecto': insumos_proyecto,
        'total_insumos': total_insumos,
        'costo_personal': costo_personal,
        'ingresos': ingresos,
        'rentabilidad': rentabilidad,
        'margen': margen,
    })


@login_required
def project_complete(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    if request.method == 'POST':
        project.estado_proyecto = 'completado'
        project.save()
        return redirect('projects')


@login_required
def project_delete(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    if request.method == 'POST':
        project.delete()
        return redirect('projects')


@login_required
def create_project(request):
    if request.method == 'GET':
        return render(request, 'create_project.html', {
            'form': ProjectForm()
        })
    else:
        try:
            form = ProjectForm(request.POST)
            new_project = form.save(commit=False)
            new_project.user = request.user
            new_project.save()
            return redirect('projects')
        except ValueError:
            return render(request, 'create_project.html', {
                'form': ProjectForm(),
                'error': 'Please provide valid data'
            })


@login_required
def create_employee(request):
    if request.method == 'GET':
        return render(request, 'create_employee.html', {'form': EmpleadoForm()})
    else:
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f"El empleado {employee.nombre} {employee.apellido_paterno} fue registrado exitosamente.")
            return redirect('employees')
        return render(request, 'create_employee.html', {
            'form': form,
            'error': 'Por favor, proporcione datos válidos'
        })


@login_required
def deactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee, activo=True)
    empleado.activo = False
    empleado.save()
    messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue inhabilitado.")
    return redirect('employees')


@login_required
def employee_view(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)
    return render(request, 'employee_view.html', {'employee': empleado})


@login_required
def employee_detail(request, id_employee):
    empleado = get_object_or_404(Empleado, pk=id_employee)
    if request.method == 'GET':
        form = EmpleadoForm(instance=empleado)
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})
    else:
        form = EmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            form.save()
            messages.success(request, f"El empleado {empleado.nombre} {empleado.apellido_paterno} fue actualizado exitosamente.")
            return redirect('employees')
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})


@login_required
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

    empleados = Empleado.objects.filter(activo=True).order_by('-id')

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
def payment_list(request):
    search_proyecto = request.GET.get('search_proyecto', '')
    filter_estado = request.GET.get('filter_estado', '')
    filter_tipo = request.GET.get('filter_tipo', '')
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
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)

    context = {
        'payments': payments_page,
        'total_payments': total_payments,
        'search_proyecto': search_proyecto,
        'filter_estado': filter_estado,
        'filter_tipo': filter_tipo,
        'per_page': per_page,
    }
    return render(request, 'payments.html', context)


@login_required
def payment_view(request, id_payment):
    payment = get_object_or_404(Pago, pk=id_payment, activo=True)
    return render(request, 'payment_view.html', {'payment': payment})


@login_required
def payment_detail(request, id_payment):
    payment = get_object_or_404(Pago, pk=id_payment, activo=True)
    if request.method == 'GET':
        form = PaymentForm(instance=payment)
        return render(request, 'payment_detail.html', {'payment': payment, 'form': form})
    else:
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, f"El pago del proyecto '{payment.proyecto.nombre}' fue actualizado exitosamente.")
            return redirect('payments')
        return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'error': "Error al actualizar el pago"})


@login_required
def deactivate_payment(request, id_payment):
    payment = get_object_or_404(Pago, id=id_payment, activo=True)
    payment.activo = False
    payment.save()
    messages.success(request, f"El pago de Bs. {payment.monto} del proyecto '{payment.proyecto.nombre}' ha sido inhabilitado.")
    return redirect('payments')


@login_required
def create_payment(request):
    if request.method == 'GET':
        return render(request, 'create_payment.html', {'form': PaymentForm()})
    else:
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            messages.success(request, f"El pago de Bs. {payment.monto} fue registrado exitosamente.")
            return redirect('payments')
        return render(request, 'create_payment.html', {
            'form': form,
            'error': 'Por favor, proporcione datos válidos'
        })


@login_required
def filter_payments_by_project_name(request):
    project_name = request.GET.get('project_name', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    filter_estado = request.GET.get('filter_estado', '')
    filter_tipo = request.GET.get('filter_tipo', '')

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

    total_monto = payments.aggregate(total=Sum('monto'))['total'] or 0
    monto_pagado = payments.filter(estado='pagado').aggregate(total=Sum('monto'))['total'] or 0
    monto_pendiente = payments.filter(estado='pendiente').aggregate(total=Sum('monto'))['total'] or 0
    count_pagado = payments.filter(estado='pagado').count()
    count_pendiente = payments.filter(estado='pendiente').count()

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
        if 'download' in request.GET:
            response['Content-Disposition'] = 'attachment; filename="reporte_pagos.pdf"'
        else:
            response['Content-Disposition'] = 'inline; filename="reporte_pagos.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    return render(request, 'payments_by_project_name.html', context)


@login_required
def payment_analysis(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payments = Pago.objects.all()

    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            payments = payments.filter(fecha__gte=start_date)
        except ValueError:
            pass

    if end_date:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            payments = payments.filter(fecha__lte=end_date)
        except ValueError:
            pass

    payment_status_counts = payments.values('estado').annotate(count=Count('estado'))
    payment_type_counts = payments.values('tipo_pago').annotate(count=Count('tipo_pago'))

    status_labels = [status['estado'] for status in payment_status_counts]
    status_values = [status['count'] for status in payment_status_counts]

    fig, ax = plt.subplots()
    ax.pie(status_values, labels=status_labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graphic = base64.b64encode(buf.getvalue()).decode('utf-8')

    context = {
        'graphic': graphic,
        'payment_status_counts': payment_status_counts,
        'payment_type_counts': payment_type_counts,
        'start_date': start_date,
        'end_date': end_date,
        'message': None if payments.exists() else 'No hay pagos en este rango de fechas.',
    }
    return render(request, 'payment_analysis.html', context)


@login_required
def create_public_entity(request):
    if request.method == 'GET':
        return render(request, 'create_public_entity.html', {
            'form': PublicEntityForm()
        })
    else:
        try:
            form = PublicEntityForm(request.POST)
            new_entity = form.save(commit=False)
            new_entity.save()
            return redirect('public_entities')
        except ValueError:
            return render(request, 'create_public_entity.html', {
                'form': PublicEntityForm(),
                'error': 'Por favor, proporcione datos válidos'
            })


@login_required
def deactivate_public_entity(request, id_public_entity):
    public_entity = get_object_or_404(EntidadPublica, id=id_public_entity)
    public_entity.activo = False
    public_entity.save()
    return redirect('public_entities')


@login_required
def public_entity_detail(request, id_public_entity):
    if request.method == 'GET':
        public_entity = get_object_or_404(EntidadPublica, pk=id_public_entity)
        form = PublicEntityForm(instance=public_entity)
        return render(request, 'public_entity_detail.html', {'public_entity': public_entity, 'form': form})
    else:
        try:
            public_entity = get_object_or_404(EntidadPublica, pk=id_public_entity)
            form = PublicEntityForm(request.POST, instance=public_entity)
            form.save()
            return redirect('public_entities')
        except ValueError:
            return render(request, 'public_entity_detail.html', {'public_entity': public_entity, 'form': form, 'error': "Error al actualizar la entidad pública"})


@login_required
def public_entities(request):
    public_entities = EntidadPublica.objects.all()
    return render(request, 'public_entities.html', {'public_entities': public_entities})


@login_required
def create_proposal(request):
    if request.method == 'GET':
        return render(request, 'create_proposal.html', {
            'form': ProposalForm()
        })
    else:
        try:
            form = ProposalForm(request.POST)
            new_proposal = form.save(commit=False)
            new_proposal.save()
            return redirect('proposals')
        except ValueError:
            return render(request, 'create_proposal.html', {
                'form': ProposalForm(),
                'error': 'Por favor, proporcione datos válidos'
            })


@login_required
def proposal_detail(request, id_proposal):
    if request.method == 'GET':
        proposal = get_object_or_404(Propuesta, pk=id_proposal)
        form = ProposalForm(instance=proposal)
        return render(request, 'proposal_detail.html', {'proposal': proposal, 'form': form})
    else:
        try:
            proposal = get_object_or_404(Propuesta, pk=id_proposal)
            form = ProposalForm(request.POST, instance=proposal)
            form.save()
            return redirect('proposals')
        except ValueError:
            return render(request, 'proposal_detail.html', {'proposal': proposal, 'form': form, 'error': "Error al actualizar la propuesta"})


@login_required
def proposals(request):
    proposals = Propuesta.objects.all()
    return render(request, 'proposals.html', {'proposals': proposals})


@login_required
def deactivate_proposal(request, id_proposal):
    proposal = get_object_or_404(Propuesta, id=id_proposal)
    proposal.activo = False
    proposal.save()
    return redirect('proposals')


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
    # cliente = get_object_or_404(Cliente, id=id_cliente)
    # cliente.delete()
    cliente = get_object_or_404(Cliente, id=id_cliente, activo=True)
    cliente.activo = False
    cliente.save()
    messages.success(request, f"El contratante {cliente.nombre} {cliente.apellido_paterno} ha sido inhabilitado exitosamente.")
    return redirect('clientes')


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard_home(request):
    # ── Proyectos ──────────────────────────────────────────────────────────────
    proyectos_qs = Proyecto.objects.filter(activo=True)
    total_proyectos = proyectos_qs.count()
    pendientes      = proyectos_qs.filter(estado_proyecto='pendiente').count()
    en_progreso     = proyectos_qs.filter(estado_proyecto='en_progreso').count()
    completados     = proyectos_qs.filter(estado_proyecto='completado').count()

    # ── Finanzas ───────────────────────────────────────────────────────────────
    total_facturado = proyectos_qs.aggregate(total=Sum('monto_total'))['total'] or 0
    total_cobrado   = Pago.objects.filter(activo=True, estado='pagado').aggregate(total=Sum('monto'))['total'] or 0
    por_cobrar      = total_facturado - total_cobrado

    # ── Entidades ──────────────────────────────────────────────────────────────
    total_clientes  = Cliente.objects.filter(activo=True).count()
    total_empleados = Empleado.objects.filter(activo=True).count()

    # ── Alertas ────────────────────────────────────────────────────────────────
    alertas = []
    completados_sin_pago = proyectos_qs.filter(
        estado_proyecto='completado', estado_pago='no_pagado'
    )
    for p in completados_sin_pago:
        alertas.append({'tipo': 'danger', 'msg': f'Proyecto "{p.nombre}" está completado pero sin cobrar.'})

    parciales_completados = proyectos_qs.filter(
        estado_proyecto='completado', estado_pago='parcial'
    )
    for p in parciales_completados:
        alertas.append({'tipo': 'warning', 'msg': f'Proyecto "{p.nombre}" completado con pago parcial pendiente.'})

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
        'total_proyectos':   total_proyectos,
        'pendientes':        pendientes,
        'en_progreso':       en_progreso,
        'completados':       completados,
        'total_facturado':   total_facturado,
        'total_cobrado':     total_cobrado,
        'por_cobrar':        por_cobrar,
        'total_clientes':    total_clientes,
        'total_empleados':   total_empleados,
        'alertas':           alertas,
        'ultimos_proyectos': ultimos_proyectos,
        'tipos_labels':      tipos_labels,
        'tipos_values':      tipos_values,
    }
    return render(request, 'home.html', context)


# ===================== PROGRESO =====================

@login_required
def create_progreso(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    if request.method == 'GET':
        form = ProgresoForm(proyecto=project)
        return render(request, 'create_progreso.html', {'form': form, 'project': project})
    else:
        form = ProgresoForm(request.POST, proyecto=project)
        if form.is_valid():
            progreso = form.save(commit=False)
            progreso.proyecto = project
            progreso.save()
            messages.success(request, 'Progreso registrado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_progreso.html', {'form': form, 'project': project})


@login_required
def progreso_detail(request, id_progreso):
    progreso = get_object_or_404(Progreso, pk=id_progreso, proyecto__user=request.user)
    project = progreso.proyecto
    if request.method == 'GET':
        form = ProgresoForm(instance=progreso, proyecto=project)
        return render(request, 'progreso_detail.html', {'form': form, 'progreso': progreso, 'project': project})
    else:
        form = ProgresoForm(request.POST, instance=progreso, proyecto=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Progreso actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'progreso_detail.html', {'form': form, 'progreso': progreso, 'project': project})


@login_required
def deactivate_progreso(request, id_progreso):
    progreso = get_object_or_404(Progreso, pk=id_progreso, proyecto__user=request.user)
    id_project = progreso.proyecto.id
    if request.method == 'POST':
        progreso.delete()
        messages.success(request, 'Registro de progreso eliminado.')
    return redirect('project_view', id_project=id_project)


# ===================== CONTRATOS =====================

@login_required
def create_contrato_empleado(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    if request.method == 'GET':
        form = ContratoEmpleadoForm()
        return render(request, 'create_contrato_empleado.html', {'form': form, 'project': project})
    else:
        form = ContratoEmpleadoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save(commit=False)
            contrato.proyecto = project
            contrato.save()
            messages.success(request, f'Contrato registrado para {contrato.empleado.nombre} {contrato.empleado.apellido_paterno}.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_contrato_empleado.html', {'form': form, 'project': project})


@login_required
def contrato_empleado_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True, proyecto__user=request.user)
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
    contrato = get_object_or_404(ContratoEmpleado, pk=id_contrato, activo=True, proyecto__user=request.user)
    if request.method == 'POST':
        contrato.activo = False
        contrato.save()
        messages.success(request, f'Contrato de {contrato.empleado.nombre} {contrato.empleado.apellido_paterno} inhabilitado.')
    return redirect('project_view', id_project=contrato.proyecto.id)


@login_required
def create_contrato_proyecto(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    # Check if project already has an active contract
    existing = getattr(project, 'contrato_proyecto', None)
    if existing and existing.activo:
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
            messages.success(request, 'Contrato del proyecto registrado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_contrato_proyecto.html', {'form': form, 'project': project})


@login_required
def contrato_proyecto_detail(request, id_contrato):
    contrato = get_object_or_404(ContratoProyecto, pk=id_contrato, activo=True, proyecto__user=request.user)
    project = contrato.proyecto
    if request.method == 'GET':
        form = ContratoProyectoForm(instance=contrato)
        return render(request, 'contrato_proyecto_detail.html', {'form': form, 'contrato': contrato, 'project': project})
    else:
        form = ContratoProyectoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contrato del proyecto actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'contrato_proyecto_detail.html', {'form': form, 'contrato': contrato, 'project': project})


@login_required
def deactivate_contrato_proyecto(request, id_contrato):
    contrato = get_object_or_404(ContratoProyecto, pk=id_contrato, activo=True, proyecto__user=request.user)
    if request.method == 'POST':
        contrato.activo = False
        contrato.save()
        messages.success(request, 'Contrato del proyecto inhabilitado.')
    return redirect('project_view', id_project=contrato.proyecto.id)


# ===================== PROVEEDORES =====================

@login_required
def proveedores(request):
    search_nombre = request.GET.get('search_nombre', '')
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

    qs = Proveedor.objects.filter(activo=True).order_by('nombre')
    if search_nombre:
        qs = qs.filter(nombre__icontains=search_nombre)

    paginator = Paginator(qs, per_page)
    try:
        proveedores_page = paginator.page(page)
    except PageNotAnInteger:
        proveedores_page = paginator.page(1)
    except EmptyPage:
        proveedores_page = paginator.page(paginator.num_pages)

    return render(request, 'proveedores.html', {
        'proveedores': proveedores_page,
        'search_nombre': search_nombre,
        'per_page': per_page,
    })


@login_required
def create_proveedor(request):
    if request.method == 'GET':
        return render(request, 'create_proveedor.html', {'form': ProveedorForm()})
    else:
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'El proveedor {proveedor.nombre} fue registrado exitosamente.')
            return redirect('proveedores')
        return render(request, 'create_proveedor.html', {'form': form})


@login_required
def proveedor_detail(request, id_proveedor):
    proveedor = get_object_or_404(Proveedor, pk=id_proveedor)
    if request.method == 'GET':
        form = ProveedorForm(instance=proveedor)
        return render(request, 'proveedor_detail.html', {'proveedor': proveedor, 'form': form})
    else:
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f'El proveedor {proveedor.nombre} fue actualizado exitosamente.')
            return redirect('proveedores')
        return render(request, 'proveedor_detail.html', {'proveedor': proveedor, 'form': form})


@login_required
def deactivate_proveedor(request, id_proveedor):
    proveedor = get_object_or_404(Proveedor, pk=id_proveedor, activo=True)
    proveedor.activo = False
    proveedor.save()
    messages.success(request, f'El proveedor {proveedor.nombre} ha sido inhabilitado.')
    return redirect('proveedores')


# ===================== INSUMOS =====================

@login_required
def insumos(request):
    search_nombre = request.GET.get('search_nombre', '')
    filter_categoria = request.GET.get('filter_categoria', '')
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

    qs = Insumo.objects.filter(activo=True).order_by('categoria', 'nombre')
    if search_nombre:
        qs = qs.filter(
            Q(nombre__icontains=search_nombre) | Q(marca__icontains=search_nombre)
        )
    if filter_categoria:
        qs = qs.filter(categoria=filter_categoria)

    paginator = Paginator(qs, per_page)
    try:
        insumos_page = paginator.page(page)
    except PageNotAnInteger:
        insumos_page = paginator.page(1)
    except EmptyPage:
        insumos_page = paginator.page(paginator.num_pages)

    from .models import Insumo as InsumoModel
    categorias = InsumoModel.CATEGORIA_CHOICES

    return render(request, 'insumos.html', {
        'insumos': insumos_page,
        'search_nombre': search_nombre,
        'filter_categoria': filter_categoria,
        'categorias': categorias,
        'per_page': per_page,
    })


@login_required
def create_insumo(request):
    if request.method == 'GET':
        return render(request, 'create_insumo.html', {'form': InsumoForm()})
    else:
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save()
            messages.success(request, f'El insumo {insumo.nombre} fue registrado exitosamente.')
            return redirect('insumos')
        return render(request, 'create_insumo.html', {'form': form})


@login_required
def insumo_detail(request, id_insumo):
    insumo = get_object_or_404(Insumo, pk=id_insumo)
    if request.method == 'GET':
        form = InsumoForm(instance=insumo)
        return render(request, 'insumo_detail.html', {'insumo': insumo, 'form': form})
    else:
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, f'El insumo {insumo.nombre} fue actualizado exitosamente.')
            return redirect('insumos')
        return render(request, 'insumo_detail.html', {'insumo': insumo, 'form': form})


@login_required
def deactivate_insumo(request, id_insumo):
    insumo = get_object_or_404(Insumo, pk=id_insumo, activo=True)
    insumo.activo = False
    insumo.save()
    messages.success(request, f'El insumo {insumo.nombre} ha sido inhabilitado.')
    return redirect('insumos')


# ===================== REQUIERE (insumos del proyecto) =====================

@login_required
def create_requiere(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project, user=request.user)
    insumos_activos = Insumo.objects.filter(activo=True)
    import json
    insumos_con_precio = {str(i.id): str(i.costo_unitario) for i in insumos_activos}

    if request.method == 'GET':
        form = RequerirForm()
        return render(request, 'create_requiere.html', {
            'form': form,
            'project': project,
            'insumos_con_precio': json.dumps(insumos_con_precio),
        })
    else:
        form = RequerirForm(request.POST)
        if form.is_valid():
            requiere = form.save(commit=False)
            requiere.proyecto = project
            requiere.save()
            messages.success(request, f'Insumo "{requiere.insumo.nombre}" agregado al proyecto.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'create_requiere.html', {
            'form': form,
            'project': project,
            'insumos_con_precio': json.dumps(insumos_con_precio),
        })


@login_required
def requiere_detail(request, id_requiere):
    requiere = get_object_or_404(Requiere, pk=id_requiere, proyecto__user=request.user)
    project = requiere.proyecto
    insumos_activos = Insumo.objects.filter(activo=True)
    import json
    insumos_con_precio = {str(i.id): str(i.costo_unitario) for i in insumos_activos}

    if request.method == 'GET':
        form = RequerirForm(instance=requiere)
        return render(request, 'requiere_detail.html', {
            'form': form,
            'requiere': requiere,
            'project': project,
            'insumos_con_precio': json.dumps(insumos_con_precio),
        })
    else:
        form = RequerirForm(request.POST, instance=requiere)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insumo del proyecto actualizado correctamente.')
            return redirect('project_view', id_project=project.id)
        return render(request, 'requiere_detail.html', {
            'form': form,
            'requiere': requiere,
            'project': project,
            'insumos_con_precio': json.dumps(insumos_con_precio),
        })


@login_required
def deactivate_requiere(request, id_requiere):
    requiere = get_object_or_404(Requiere, pk=id_requiere, proyecto__user=request.user)
    id_project = requiere.proyecto.id
    if request.method == 'POST':
        requiere.delete()
        messages.success(request, 'Insumo eliminado del proyecto.')
    return redirect('project_view', id_project=id_project)


# ===================== COMPRAS (Realizar) =====================

@login_required
def compras(request):
    search = request.GET.get('search', '')
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

    qs = Realizar.objects.select_related('proveedor', 'insumo').order_by('-fecha')
    if search:
        qs = qs.filter(
            Q(insumo__nombre__icontains=search) | Q(proveedor__nombre__icontains=search)
        )

    paginator = Paginator(qs, per_page)
    try:
        compras_page = paginator.page(page)
    except PageNotAnInteger:
        compras_page = paginator.page(1)
    except EmptyPage:
        compras_page = paginator.page(paginator.num_pages)

    return render(request, 'compras.html', {
        'compras': compras_page,
        'search': search,
        'per_page': per_page,
    })


@login_required
def create_realizar(request):
    if request.method == 'GET':
        return render(request, 'create_realizar.html', {'form': RealizarForm()})
    else:
        form = RealizarForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.costo_total = compra.cantidad * compra.costo_unitario
            compra.save()
            messages.success(request, f'Compra registrada: {compra.insumo.nombre} x{compra.cantidad} de {compra.proveedor.nombre}.')
            return redirect('compras')
        return render(request, 'create_realizar.html', {'form': form})


@login_required
def realizar_detail(request, id_realizar):
    compra = get_object_or_404(Realizar, pk=id_realizar)
    if request.method == 'GET':
        form = RealizarForm(instance=compra)
        return render(request, 'realizar_detail.html', {'compra': compra, 'form': form})
    else:
        form = RealizarForm(request.POST, instance=compra)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.costo_total = compra.cantidad * compra.costo_unitario
            compra.save()
            messages.success(request, 'Compra actualizada correctamente.')
            return redirect('compras')
        return render(request, 'realizar_detail.html', {'compra': compra, 'form': form})


@login_required
def deactivate_realizar(request, id_realizar):
    compra = get_object_or_404(Realizar, pk=id_realizar)
    if request.method == 'POST':
        compra.delete()
        messages.success(request, 'Compra eliminada correctamente.')
    return redirect('compras')
