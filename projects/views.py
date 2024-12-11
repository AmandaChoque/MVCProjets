
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.http import HttpResponse
from django.db import IntegrityError

from .form import ProjectForm, EmployeeForm, PaymentForm, PublicEntityForm, ProposalForm, ContractorForm
from .models import Project, Employee, Payment, PublicEntity, Proposal, Contractor
from django.contrib.auth.decorators import login_required

from django.utils import timezone
# Create your views here.
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Project



# views.py
from django.shortcuts import render
from django.http import HttpResponse
from .models import Project
import matplotlib.pyplot as plt
import io
import urllib, base64

from django.shortcuts import render
from django.utils import timezone
from .models import Project
from django.db.models import Q

import matplotlib.pyplot as plt
import io
import base64
from django.shortcuts import render
from django.utils import timezone
from .models import Project
from django.db.models import Count


from django.views.generic import ListView, CreateView


from django.utils.timezone import now


from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Payment, Project
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
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
                login(request, user) # crea cookie sesionid (tiene fecha de espiracion), si la tarea a crreado este usuario, o permisos
                
                return redirect('projects') # redirecciono a la ruta name = projects
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
    return redirect('home')

def signin(request):
    if request.method == 'GET':
        return render(request, 'signin.html', {
            'form': AuthenticationForm
        })
    else:
        print(request.POST)
        user =authenticate(request, username=request.POST['username'], password=request.POST['password']) #son validos los datos que me envian
        
        if user is None:
            return render(request, 'signin.html', {
                'form': AuthenticationForm,
                'error': 'Username or password is incorrect'
            })
        else:
            login(request, user)
            return redirect('projects')

@login_required
def reporte_analisis_view(request):
    # Obtén los conteos de proyectos según su estado
    total_completados = Project.objects.filter(project_status='completado').count()
    total_en_progreso = Project.objects.filter(project_status='en_progreso').count()
    total_pendientes = Project.objects.filter(project_status='pendiente').count()

    # Datos para el gráfico
    labels = ['Completado', 'En Progreso', 'Pendiente']
    sizes = [total_completados, total_en_progreso, total_pendientes]
    colors = ['#4CAF50', '#FFEB3B', '#F44336']
    explode = (0.1, 0, 0)

    # Crear el gráfico de torta con un tamaño más pequeño
    plt.figure(figsize=(4, 4))  # Cambia aquí el tamaño de la figura
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, explode=explode)
    plt.axis('equal')

    # Convertir el gráfico a una imagen
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')  # 'bbox_inches' ayuda a ajustar el espacio
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')

    # Pasar el gráfico al template
    context = {'graphic': graphic}
    return render(request, 'reporte_analisis.html', context)

@login_required
def project_analysis(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    projects = Project.objects.all()

    if start_date:
        projects = projects.filter(start_date__gte=start_date)
    if end_date:
        projects = projects.filter(end_date__lte=end_date)

    # Verificar si hay proyectos en el rango
    if not projects.exists():
        context = {
            'message': "No existen proyectos en el rango de fechas seleccionado.",
            'start_date': start_date,
            'end_date': end_date,
        }
        return render(request, 'project_analysis.html', context)

    # Contar proyectos por tipo
    project_counts = projects.values('project_type').annotate(total=Count('project_type'))
    licitacion_count = next((item['total'] for item in project_counts if item['project_type'] == 'licitacion'), 0)
    contratacion_count = next((item['total'] for item in project_counts if item['project_type'] == 'contratacion_directa'), 0)

    # Generar gráfico de torta
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
    project_status = request.GET.get('project_status')  # Nuevo filtro por estado del proyecto

    projects = Project.objects.all()

    if start_date:
        projects = projects.filter(start_date__gte=start_date)
    if end_date:
        projects = projects.filter(end_date__lte=end_date)
    if project_type:
        projects = projects.filter(project_type=project_type)
    if project_status:
        projects = projects.filter(project_status=project_status)

    context = {
        'projects': projects,
        'start_date': start_date,
        'end_date': end_date,
        'project_type': project_type,
        'project_status': project_status,
        'now': timezone.now(),  # Fecha y hora actual
    }

    # Renderizado del PDF
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

# proyects
@login_required
def projects(request):
    # projects = Project.objects.all()
    projects = Project.objects.filter(user= request.user, project_status__in =['pendiente', 'en_progreso'],
    is_active=True)
    return render(request, 'projects.html', {
        'projects': projects
    })

@login_required
def deactivate_project(request, id_project):
    project = get_object_or_404(Project, id=id_project, user=request.user)
    project.is_active = False
    project.deleted_at = timezone.now()  # Registrar la fecha de eliminación
    project.save()
    return redirect('projects')

@login_required
def projects_completed(request):
    projects = Project.objects.filter(user= request.user, project_status__in =['completado'], is_active=True)
    return render(request, 'projects_completes.html', {
        'projects': projects
    })

@login_required
def project_detail(request, id_project):
    # para que pueda ver sosl sus proyectos
    project = get_object_or_404(Project, pk = id_project, user=request.user)
    if request.method == 'GET':
        form = ProjectForm(instance=project)
        return render(request, 'project_detail.html', {
            'project': project,
            'form': form
        })
    else:
        try:
            form = ProjectForm(request.POST, instance=project)
            form.save()
            return redirect('projects')
        except ValueError:
            return render(request, 'project_detail.html', {'project': project, 'form': form, 'error': "Error al actualizar el proyecto"})

@login_required
def project_complete(request, id_project):
    project =get_object_or_404(Project, pk = id_project, user = request.user)
    if request.method == 'POST':
        project.project_status = 'Completado'
        project.save()
        return redirect('projects')

@login_required
def project_delete(request, id_project):
    project =get_object_or_404(Project, pk = id_project, user = request.user)
    if request.method == 'POST':
        project.delete()
        return redirect('projects')

@login_required  
def create_project(request):
    if request.method =='GET':
        return render(request, 'create_project.html', {
            'form': ProjectForm
        })
    else:
        try:
            #print(request.POST)
            form = ProjectForm(request.POST)
            new_project =form.save(commit=False)
            new_project.user = request.user
            new_project.save()
            return redirect('projects')
        
        except ValueError:
            return render(request, 'create_project.html', {
                'form': ProjectForm,
                'error': 'Please provide valida data'
            })

# employee
@login_required  
def create_employee(request):
    if request.method =='GET':
        return render(request, 'create_employee.html', {
            'form': EmployeeForm
        })
    else:
        try:
            print(request.POST)
            form = EmployeeForm(request.POST)
            new_project =form.save(commit=False)
            #new_project.user = User.objects.first()
            #  employee.user = form.cleaned_data['user']  # Asegúrate de que 'user' está en el formulario
            # new_project.user = request.user
            new_project.save()
            return redirect('employees')
        
        except ValueError:
            return render(request, 'create_employee.html', {
                'form': EmployeeForm,
                'error': 'Please provide valida data'
            })

@login_required
def deactivate_employee(request, id_employee):
    employee = get_object_or_404(Employee, id=id_employee)
    employee.is_active = False
    employee.deleted_at = timezone.now()  # Registrar la fecha de eliminación
    employee.save()
    return redirect('employees')

@login_required
def employee_detail(request, id_employee):
    # para que pueda ver sosl sus proyectos
    if request.method == 'GET':
        employee = get_object_or_404(Employee, pk = id_employee)
        form = EmployeeForm(instance=employee)
        return render(request, 'employee_detail.html', {
            'employee': employee,
            'form': form
        })
    else:
        try:
            employee = get_object_or_404(Employee, pk = id_employee)
            form = EmployeeForm(request.POST, instance=employee)
            form.save()
            return redirect('employees')
        except ValueError:
            return render(request, 'employee_detail.html', {'employee': employee, 'form': form, 'error': "Error al actualizar el empleado"})

@login_required
def employees(request):
    employees = Employee.objects.all()
    # employess = Employee.objects.filter(user= request.user, project_status__in =['pendiente', 'en_progreso'])
    return render(request, 'employees.html', {
        'employees': employees
    })

# PAYMENTS

# @login_required
# def list_payments(request):
#     payments = Payment.objects.all()
#     return render(request, 'list_payments.html', {'payments': payments})

@login_required
def payment_list(request):

    payments = Payment.objects.all()
    # projects = Project.objects.filter(user= request.user)
    return render(request, 'payments.html', {
        'payments': payments
    })

@login_required
def payment_detail(request, id_payment):
    # para que pueda ver sosl sus proyectos
    payment = get_object_or_404(Payment, pk = id_payment)
    
    if request.method == 'GET':
        form = PaymentForm(instance=payment)
        return render(request, 'payment_detail.html', {
            'payment': payment,
            'form': form
        })
    else:
        try:
            form = PaymentForm(request.POST, instance=payment)
            form.save()
            return redirect('payments')
        except ValueError:
            return render(request, 'payment_detail.html', {'payment': payment, 'form': form, 'error': "Error al actualizar el proyecto"})

@login_required
def deactivate_payment(request, id_payment):
    payment = get_object_or_404(Payment, id=id_payment)
    payment.is_active = False
    payment.deleted_at = timezone.now()  # Registrar la fecha de eliminación
    payment.save()
    return redirect('payments')

@login_required
def create_payment(request):
    if request.method =='GET':
        return render(request, 'create_payment.html', {
            'form': PaymentForm
        })
    else:
        try:
            print(request.POST)
            form = PaymentForm(request.POST)
            new_project =form.save(commit=False)
            #new_project.user = User.objects.first()
            #  payment.user = form.cleaned_data['user']  # Asegúrate de que 'user' está en el formulario
            # new_project.user = request.user
            new_project.save()
            return redirect('payments')
        
        except ValueError:
            return render(request, 'create_payment.html', {
                'form': PaymentForm,
                'error': 'Please provide valida data'
            })

@login_required
def filter_payments_by_project_name(request):
    # Recuperar los parámetros de filtro desde la URL
    project_name = request.GET.get('project_name', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Obtener todos los proyectos con nombres únicos
    projects = Project.objects.values('name').distinct()

    # Filtrar pagos por nombre de proyecto y fechas
    payments = Payment.objects.all()

    if project_name:
        payments = payments.filter(project__name__icontains=project_name)

    if start_date:
        payments = payments.filter(date__gte=start_date)  # Cambié payment_date por date

    if end_date:
        payments = payments.filter(date__lte=end_date)  # Cambié payment_date por date

    context = {
        'payments': payments,
        'projects': projects,  # Pasar los proyectos al contexto
        'project_name': project_name,
        'start_date': start_date,
        'end_date': end_date,
        'now': timezone.now(),  # Fecha y hora actual
    }
    # Renderizado del PDF
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

    # Filtrar pagos según fechas
    payments = Payment.objects.all()

    # Filtramos por fecha de inicio
    if start_date:
        try:
            # Convertimos la fecha de inicio al formato datetime.date
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            payments = payments.filter(date__gte=start_date)  # Filtrar por fecha de pago mayor o igual
        except ValueError:
            pass  # Si el formato es incorrecto, no se aplica el filtro

    # Filtramos por fecha de fin
    if end_date:
        try:
            # Convertimos la fecha de fin al formato datetime.date
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            payments = payments.filter(date__lte=end_date)  # Filtrar por fecha de pago menor o igual
        except ValueError:
            pass  # Si el formato es incorrecto, no se aplica el filtro

    # Contar pagos por estado y tipo
    payment_status_counts = payments.values('status').annotate(count=Count('status'))
    payment_type_counts = payments.values('payment_type').annotate(count=Count('payment_type'))

    # Crear gráfico de torta para estado de pago
    status_labels = [status['status'] for status in payment_status_counts]
    status_values = [status['count'] for status in payment_status_counts]

    fig, ax = plt.subplots()
    ax.pie(status_values, labels=status_labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Convertir gráfico a imagen base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    graphic = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Enviar contexto a la plantilla
    context = {
        'graphic': graphic,
        'payment_status_counts': payment_status_counts,
        'payment_type_counts': payment_type_counts,
        'start_date': start_date,
        'end_date': end_date,
        'message': None if payments.exists() else 'No hay pagos en este rango de fechas.',
    }

    return render(request, 'payment_analysis.html', context)
   
# Public Entity
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
            return redirect('public_entities')  # Cambiar según el nombre de la vista que muestra las entidades públicas
        except ValueError:
            return render(request, 'create_public_entity.html', {
                'form': PublicEntityForm(),
                'error': 'Por favor, proporcione datos válidos'
            })

@login_required
def deactivate_public_entity(request, id_public_entity):
    public_entity = get_object_or_404(PublicEntity, id=id_public_entity)
    public_entity.delete()
    return redirect('public_entities')

@login_required
def public_entity_detail(request, id_public_entity):
    if request.method == 'GET':
        public_entity = get_object_or_404(PublicEntity, pk=id_public_entity)
        form = PublicEntityForm(instance=public_entity)
        return render(request, 'public_entity_detail.html', {
            'public_entity': public_entity,
            'form': form
        })
    else:
        try:
            public_entity = get_object_or_404(PublicEntity, pk=id_public_entity)
            form = PublicEntityForm(request.POST, instance=public_entity)
            form.save()
            return redirect('public_entities')
        except ValueError:
            return render(request, 'public_entity_detail.html', {
                'public_entity': public_entity,
                'form': form,
                'error': "Error al actualizar la entidad pública"
            })

@login_required
def public_entities(request):
    public_entities = PublicEntity.objects.all()
    return render(request, 'public_entities.html', {
        'public_entities': public_entities
    })

# Proporsal
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
            return redirect('proposals')  # Cambiar según el nombre de la vista que muestra las propuestas
        except ValueError:
            return render(request, 'create_proposal.html', {
                'form': ProposalForm(),
                'error': 'Por favor, proporcione datos válidos'
            })

@login_required
def proposal_detail(request, id_proposal):
    if request.method == 'GET':
        proposal = get_object_or_404(Proposal, pk=id_proposal)
        form = ProposalForm(instance=proposal)
        return render(request, 'proposal_detail.html', {
            'proposal': proposal,
            'form': form
        })
    else:
        try:
            proposal = get_object_or_404(Proposal, pk=id_proposal)
            form = ProposalForm(request.POST, instance=proposal)
            form.save()
            return redirect('proposals')
        except ValueError:
            return render(request, 'proposal_detail.html', {
                'proposal': proposal,
                'form': form,
                'error': "Error al actualizar la propuesta"
            })

@login_required
def proposals(request):
    proposals = Proposal.objects.all()
    return render(request, 'proposals.html', {
        'proposals': proposals
    })

@login_required
def deactivate_proposal(request, id_proposal):
    proposal = get_object_or_404(Proposal, id=id_proposal)
    proposal.delete()
    return redirect('proposals')

# Contractor
@login_required  
def create_contractor(request):
    if request.method == 'GET':
        return render(request, 'create_contractor.html', {
            'form': ContractorForm()
        })
    else:
        try:
            form = ContractorForm(request.POST)
            new_contractor = form.save(commit=False)
            new_contractor.save()
            return redirect('contractors')  # Cambiar según el nombre de la vista que muestra los contratantes
        except ValueError:
            return render(request, 'create_contractor.html', {
                'form': ContractorForm(),
                'error': 'Por favor, proporcione datos válidos'
            })

@login_required
def contractor_detail(request, id_contractor):
    if request.method == 'GET':
        contractor = get_object_or_404(Contractor, pk=id_contractor)
        form = ContractorForm(instance=contractor)
        return render(request, 'contractor_detail.html', {
            'contractor': contractor,
            'form': form
        })
    else:
        try:
            contractor = get_object_or_404(Contractor, pk=id_contractor)
            form = ContractorForm(request.POST, instance=contractor)
            form.save()
            return redirect('contractors')
        except ValueError:
            return render(request, 'contractor_detail.html', {
                'contractor': contractor,
                'form': form,
                'error': "Error al actualizar el contratante"
            })

@login_required
def contractors(request):
    contractors = Contractor.objects.all()
    return render(request, 'contractors.html', {
        'contractors': contractors
    })

@login_required
def deactivate_contractor(request, id_contractor):
    contractor = get_object_or_404(Contractor, id=id_contractor)
    contractor.delete()
    return redirect('contractors')
