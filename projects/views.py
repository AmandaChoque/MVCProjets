
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.http import HttpResponse
from django.db import IntegrityError

from .form import ProjectForm, EmployeeForm
from .models import Project, Employee, Payment, PaymentHistory, Proposal, PublicEntity, Contractor
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
def render_pdf_view(request):
    projects = Project.objects.all()
    template_path = 'reporte_proyectos.html'
    context = {'projects': projects}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_proyectos.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(
       html, dest=response)

    if pisa_status.err:
       return HttpResponse('Error al generar el reporte PDF', status=500)
    return response

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
    return render(request, 'projects.html', {
        'projects': projects
    })

@login_required
def project_detail(request, id_project):
    # para que pueda ver sosl sus proyectos
    if request.method == 'GET':
        project = get_object_or_404(Project, pk = id_project, user=request.user)
        form = ProjectForm(instance=project)
        return render(request, 'project_detail.html', {
            'project': project,
            'form': form
        })
    else:
        try:
            project = get_object_or_404(Project, pk = id_project, user=request.user)
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
            print(request.POST)
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


# employees
@login_required
def employees(request):
    employees = Employee.objects.all()
    # employess = Employee.objects.filter(user= request.user, project_status__in =['pendiente', 'en_progreso'])
    return render(request, 'employees.html', {
        'employees': employees
    })

@login_required
def employee_detail(request, id_employee):
    # para que pueda ver sosl sus proyectos
    if request.method == 'GET':
        employee = get_object_or_404(Employee, pk = id_employee, user=request.user)
        form = EmployeeForm(instance=employee)
        return render(request, 'employee_detail.html', {
            'employee': employee,
            'form': form
        })
    

# Historial de pagos
@login_required
def payment_histories(request):
    payment_histories = PaymentHistory.objects.all()
    # projects = Project.objects.filter(user= request.user)
    return render(request, 'payment_histories.html', {
        'payment_histories': payment_histories
    })