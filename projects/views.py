from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages

from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError

from .form import ProjectForm, EmpleadoForm, PaymentForm, PublicEntityForm, ProposalForm, ClienteForm
from .models import Proyecto, Empleado, Pago, EntidadPublica, Propuesta, Cliente
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.db.models import Q, Count

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
        print("Entra al metodo GET ---------")
        return render(request, 'signup.html', {
            'form': UserCreationForm
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            print(request.POST)
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
        print(request.POST)
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            return render(request, 'signin.html', {
                'form': AuthenticationForm,
                'error': 'Username or password is incorrect'
            })
        else:
            login(request, user)
            return redirect('projects')


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
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    projects = Proyecto.objects.all()

    if start_date:
        projects = projects.filter(fecha_inicio__gte=start_date)
    if end_date:
        projects = projects.filter(fecha_fin__lte=end_date)

    if not projects.exists():
        context = {
            'message': "No existen proyectos en el rango de fechas seleccionado.",
            'start_date': start_date,
            'end_date': end_date,
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
        'start_date': start_date,
        'end_date': end_date,
        'licitacion_count': licitacion_count,
        'contratacion_count': contratacion_count,
    }
    return render(request, 'project_analysis.html', context)


@login_required
def project_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    project_type = request.GET.get('project_type')
    project_status = request.GET.get('project_status')

    projects = Proyecto.objects.all()

    if start_date:
        projects = projects.filter(fecha_inicio__gte=start_date)
    if end_date:
        projects = projects.filter(fecha_fin__lte=end_date)
    if project_type:
        projects = projects.filter(tipo_proyecto=project_type)
    if project_status:
        projects = projects.filter(estado_proyecto=project_status)

    context = {
        'projects': projects,
        'start_date': start_date,
        'end_date': end_date,
        'project_type': project_type,
        'project_status': project_status,
        'now': timezone.now(),
    }

    if 'pdf' in request.GET:
        template = get_template('project_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_proyectos.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    return render(request, 'project_report.html', context)


@login_required
def projects(request):
    projects = Proyecto.objects.filter(user=request.user, estado_proyecto__in=['pendiente', 'en_progreso'], activo=True)
    return render(request, 'projects.html', {'projects': projects})


@login_required
def deactivate_project(request, id_project):
    project = get_object_or_404(Proyecto, id=id_project, user=request.user)
    project.activo = False
    project.deleted_at = timezone.now()
    project.save()
    return redirect('projects')


@login_required
def projects_completed(request):
    projects = Proyecto.objects.filter(user=request.user, estado_proyecto__in=['completado'], activo=True)
    return render(request, 'projects_completes.html', {'projects': projects})


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
        return render(request, 'create_employee.html', {
            'form': EmpleadoForm()
        })
    else:
        try:
            print(request.POST)
            form = EmpleadoForm(request.POST)
            new_employee = form.save(commit=False)
            new_employee.save()
            return redirect('employees')
        except ValueError:
            return render(request, 'create_employee.html', {
                'form': EmpleadoForm(),
                'error': 'Please provide valid data'
            })


@login_required
def deactivate_employee(request, id_employee):
    empleado = get_object_or_404(Empleado, id=id_employee)
    empleado.activo = False
    empleado.deleted_at = timezone.now()
    empleado.save()
    return redirect('employees')


@login_required
def employee_detail(request, id_employee):
    if request.method == 'GET':
        empleado = get_object_or_404(Empleado, pk=id_employee)
        form = EmpleadoForm(instance=empleado)
        return render(request, 'employee_detail.html', {'employee': empleado, 'form': form})
    else:
        try:
            empleado = get_object_or_404(Empleado, pk=id_employee)
            form = EmpleadoForm(request.POST, instance=empleado)
            form.save()
            return redirect('employees')
        except ValueError:
            return render(request, 'employee_detail.html', {'employee': empleado, 'form': form, 'error': "Error al actualizar el empleado"})


@login_required
def employees(request):
    empleados = Empleado.objects.all()
    return render(request, 'employees.html', {'employees': empleados})


@login_required
def payment_list(request):
    payments = Pago.objects.all()
    return render(request, 'payments.html', {'payments': payments})


@login_required
def payment_detail(request, id_payment):
    payment = get_object_or_404(Pago, pk=id_payment)
    if request.method == 'GET':
        form = PaymentForm(instance=payment)
        return render(request, 'payment_detail.html', {'payment': payment, 'form': form})
    else:
        try:
            form = PaymentForm(request.POST, instance=payment)
            form.save()
            return redirect('payments')
        except ValueError:
            return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'error': "Error al actualizar el pago"})


@login_required
def deactivate_payment(request, id_payment):
    payment = get_object_or_404(Pago, id=id_payment)
    payment.activo = False
    payment.deleted_at = timezone.now()
    payment.save()
    return redirect('payments')


@login_required
def create_payment(request):
    if request.method == 'GET':
        return render(request, 'create_payment.html', {
            'form': PaymentForm()
        })
    else:
        try:
            print(request.POST)
            form = PaymentForm(request.POST)
            new_payment = form.save(commit=False)
            new_payment.save()
            return redirect('payments')
        except ValueError:
            return render(request, 'create_payment.html', {
                'form': PaymentForm(),
                'error': 'Please provide valid data'
            })


@login_required
def filter_payments_by_project_name(request):
    project_name = request.GET.get('project_name', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    projects = Proyecto.objects.values('nombre').distinct()
    payments = Pago.objects.all()

    if project_name:
        payments = payments.filter(proyecto__nombre__icontains=project_name)
    if start_date:
        payments = payments.filter(fecha__gte=start_date)
    if end_date:
        payments = payments.filter(fecha__lte=end_date)

    context = {
        'payments': payments,
        'projects': projects,
        'project_name': project_name,
        'start_date': start_date,
        'end_date': end_date,
        'now': timezone.now(),
    }

    if 'pdf' in request.GET:
        template = get_template('payments_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_pagos.pdf"'
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
    public_entity.delete()
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
    proposal.delete()
    return redirect('proposals')


@login_required
def create_cliente(request):
    if request.method == 'GET':
        return render(request, 'crear_cliente.html', {
            'form': ClienteForm()
        })
    else:
        try:
            form = ClienteForm(request.POST)
            new_cliente = form.save(commit=False)
            new_cliente.save()
            return redirect('clientes')
        except ValueError:
            return render(request, 'crear_cliente.html', {
                'form': ClienteForm(),
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
    clientes = Cliente.objects.filter(activo=True).order_by('id')
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
    
    # print("TOTAL QUERYSET:", clientes.count())
    # print("PER PAGE:", per_page)
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
    return render(request, 'landing.html')


@login_required
def dashboard_home(request):
    return render(request, 'home.html')
