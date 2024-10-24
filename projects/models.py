from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Project(models.Model):
    PROJECT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),         # Pendiente
        ('en_progreso', 'En Progreso'), # En Proceso
        ('completado', 'Completado'),     # Terminado
    ]
    
    PROJECT_TYPE_CHOICES = [
        ('licitacion', 'Licitación'),            # Licitación
        ('contratacion_directa', 'Contratación Directa'),  # Contratación directa
    ]
    # Fields
    code = models.CharField(max_length=20, unique=True, verbose_name="Proyecto Codigo")
    name = models.CharField(max_length=200, unique=True, verbose_name="Proyecto Nombre")
    description = models.TextField(blank=True, verbose_name="Proyecto Descripcion")
    start_date = models.DateField(verbose_name="Fecha Inicio Proyecto")
    end_date = models.DateField(null=True, blank=True, verbose_name="Fecha Final Proyecto")
    project_status = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='pendiente', verbose_name="Proyecto Estado")
    project_type = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES, default='contratacion_directa', verbose_name="Proyecto Tipo")
    photo_signed_contract = models.ImageField(upload_to="contrato_firmado",null = True, blank= True, verbose_name="Contrato Firmado")
    photo_proposed_contract = models.ImageField(upload_to="contrato_propueso",null = True, blank= True, verbose_name="Contrato Propuesto")
    
    created =models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)# Projects principal 
    
    def __str__(self):
        return self.name + ' - by '+ self.user.username