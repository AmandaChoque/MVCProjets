
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from django.http import HttpResponse
from django.db import IntegrityError

from .form import ProjectForm
from .models import Project
# Create your views here.


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

def projects(request):
    # projects = Project.objects.all()
    projects = Project.objects.filter(user= request.user, project_status__in =['pendiente', 'en_progreso'])
    return render(request, 'projects.html', {
        'projects': projects
    })

def projects_completed(request):
    projects = Project.objects.filter(user= request.user, project_status__in =['completado'])
    return render(request, 'projects.html', {
        'projects': projects
    })

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

def project_complete(request, id_project):
    project =get_object_or_404(Project, pk = id_project, user = request.user)
    if request.method == 'POST':
        project.project_status = 'Completado'
        project.save()
        return redirect('projects')
    
def project_delete(request, id_project):
    project =get_object_or_404(Project, pk = id_project, user = request.user)
    if request.method == 'POST':
        project.delete()
        return redirect('projects')
  
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
            
def signout(request):
    logout()
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
        