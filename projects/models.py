from django.utils import timezone  # Asegúrate de importar timezone desde django.utils

from django.db import models
from django.contrib.auth.models import User

# Señal para actualizar automáticamente el estado del proyecto
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.db.models import Sum
# Create your models here.

# Auditoria
class AuditModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha Actualización")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Eliminación")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        abstract = True


# Contratante
class Contractor(models.Model):
    
    ACCOUNTANT_TYPE_CHOICES = [
        ('company', 'Empresa'),
        ('personal', 'Personal'),
        ('public_entity', 'Entidad Pública'),
    ]
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    entity_place_representation = models.CharField(max_length=50, verbose_name="Entidad/Lugar/Representación")
    position = models.CharField(max_length=50, verbose_name="Cargo")  # e.g. President, Legal Representative
    nit_ci = models.CharField(max_length=20, verbose_name="NIT/CI")  # ID number
    first_name = models.CharField(max_length=50, verbose_name="Nombre")
    paternal_last_name = models.CharField(max_length=50, verbose_name="Apellido Paterno")
    maternal_last_name = models.CharField(max_length=50, verbose_name="Apellido Materno")
    phone_number = models.CharField(max_length=15, verbose_name="Número de Teléfono")
    address = models.CharField(max_length=255, verbose_name="Dirección")
    accountant_type = models.CharField(max_length=20, choices=ACCOUNTANT_TYPE_CHOICES, default='public_entity', verbose_name="Tipo Contratante")  # Valor predeterminado
    created =models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = 'Contractor'
        verbose_name_plural = 'Contractors'

    def __str__(self):
        return f"{self.first_name} {self.paternal_last_name} ({self.entity_place_representation})"
    

# Empleado
class Employee(models.Model):
    # Opciones para el campo "cargo"
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")  # Relación uno a uno con User
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    POSITION_CHOICES = [
        ('gerente_general', 'Gerente General'),
        ('tecnico', 'Técnico'),
        ('analista', 'Analista'),
        ('desarrollador', 'Desarrollador'),
    ]

    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name_father = models.CharField(max_length=100, verbose_name="Apellido Paterno")
    last_name_mother = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apellido Materno")
    phone_number = models.CharField(max_length=15, blank=True, verbose_name="Numero Celular")
    
    hire_date = models.DateField(null=True, blank=True, verbose_name="Fecha Contratación")  # No obligatorio
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Salario")  # No obligatorio
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,  # Diccionario de opciones
        default='gerente_general',  # Valor predeterminado
        verbose_name="Cargo"
    )
    # New CI field
    ci = models.CharField(max_length=20, unique=True, verbose_name="Carnet de Identidad")
    created =models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return f"{self.first_name} {self.last_name_father} {self.last_name_mother or ''} - CI: {self.ci}"
        #return f"{self.first_name} {self.last_name}"
        #return f"{self.first_name} {self.last_name}"

# EntidadPublica
class PublicEntity(models.Model):
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    legal_representative = models.CharField(max_length=200, verbose_name="Representante Legal")  # Representante Legal
    contact = models.CharField(max_length=100, verbose_name="Contacto")  # Contacto
    address = models.CharField(max_length=300, verbose_name="Direccion")  # Dirección
    entity_name = models.CharField(max_length=200, verbose_name="Nombre Entidad")  # Nombre Entidad
    created =models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = 'Public Entity'
        verbose_name_plural = 'Public Entities'

    def __str__(self):
        return self.entity_name

# Propuesta
class Proposal(models.Model):
    # Campos de la propuesta
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    submission_date = models.DateField(verbose_name="Fecha de presentación")  # Fecha de presentación
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto presupuesto")  # Monto presupuesto
    requirements = models.TextField(verbose_name="Requerimientos")  # Requerimientos

    # Relaciones
    public_entity = models.ForeignKey(PublicEntity, on_delete=models.CASCADE, related_name='proposals', verbose_name="Entidad pública")  # Entidad pública (1 a N)
    # project = models.OneToOneField(Project, on_delete=models.CASCADE, verbose_name="Project")  # Proyecto (1 a 1)

    created =models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = 'Proposal'
        verbose_name_plural = 'Proposals'

    def __str__(self):
        return f"Proposal for {self.public_entity} - Project: {self.project}"

# Proyecto
class Project(AuditModel):
    PROJECT_STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),         # Pendiente
        ('en_progreso', 'En Progreso'), # En Proceso
        ('completado', 'Completado'),     # Terminado
    ]
    
    PROJECT_TYPE_CHOICES = [
        ('licitacion', 'Licitación'),            # Licitación
        ('contratacion_directa', 'Contratación Directa'),  # Contratación directa
    ]
    # Opciones para el estado del pago
    PAYMENT_STATE_CHOICES = [
        ('no_pagado', 'No Pagado'),
        ('parcial', 'Pago Parcial'),
        ('pagado', 'Pagado Completo'),
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
    # photo_proposed_contract = models.ImageField(upload_to="contrato_propueso",null = True, blank= True, verbose_name="Contrato Propuesto")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATE_CHOICES, default='no_pagado', verbose_name="Estado de Pago")

    # created =models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)# Empleado que herede de user
    assigned_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Empleado Asignado")
    contractor = models.ForeignKey(Contractor, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Contratista")
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Propuesta")

    is_active = models.BooleanField(default=True, verbose_name="Activo")
    

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total del Proyecto")
    
    def __str__(self):
        return self.name + ' - by '+ self.user.username
    
    # def is_fully_paid(self):
    #     total_paid = self.payments.filter(status='pagado').aggregate(total_paid=Sum('amount'))['total_paid'] or 0
    #     return total_paid >= self.total_amount
    def update_payment_status(self):
        """
        Actualiza el estado de pago del proyecto basado en los pagos realizados.
        """
        total_paid = self.payments.filter(status='pagado').aggregate(total_paid=Sum('amount'))['total_paid'] or 0

        if total_paid >= self.total_amount:
            self.payment_status = 'pagado'
        elif total_paid > 0:
            self.payment_status = 'parcial'
        else:
            self.payment_status = 'no_pagado'

        self.save()

# Pago
class Payment(models.Model):
    # Opciones para el estado del pago
    PAYMENT_STATUS_CHOICES = [
        ('pagado', 'Pagado'),  # Pagado
        ('pendiente', 'Pendiente'),  # Pendiente
    ]
    
    # Opciones para el tipo de pago
    PAYMENT_TYPE_CHOICES = [
        ('parcial', 'Parcial'),  # Parcial
        ('completo', 'Completo'),  # Completo
    ]

    # Campos del modelo Payment
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")  # Monto
    date = models.DateField(verbose_name="Fecha Pago")  # Fecha
    status = models.CharField(max_length=10,  choices=PAYMENT_STATUS_CHOICES, default='pagado', verbose_name="Estado Pago")  # Estado del pago
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='parcial', verbose_name="Tipo Pago")  # Tipo de pago
    
    # Clave foránea a Project
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='payments', verbose_name="Proyecto")  # Relación (1 a N)
    created =models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"Payment of {self.amount} on {self.date} - Status: {self.status}"

    def is_payment_complete(self):
        if self.payment_type == 'completo' and self.status == 'pagado':
            return self.amount >= self.project.total_amount
        return False

    # def update_payment_status(self):
    #     if self.amount >= self.project.total_amount:
    #         self.status = 'pagado'
    #     else:
    #         self.status = 'pendiente'
    #     self.save()
    def update_payment_status(self):
        """
        Actualiza el estado del pago y sincroniza el estado de pago del proyecto.
        """
        # Actualizar estado del pago
        if self.amount >= self.project.total_amount:
            self.status = 'pagado'
        else:
            self.status = 'pendiente'
        self.save()

        # Actualizar estado de pago del proyecto
        self.project.update_payment_status()

# HistorialPagos
class PaymentHistory(models.Model):
    # Campos del historial de pagos
    modification_date = models.DateTimeField(auto_now=True, verbose_name="Modification Date")  # Fecha de modificación
    previous_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Previous Amount")  # Monto anterior
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Current Amount")  # Monto actual
    change_reason = models.TextField(verbose_name="Change Reason")  # Motivo del cambio

    # Relaciones
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='payment_histories', verbose_name="Project")  # Project (1 a N)
    created =models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'

    def __str__(self):
        return f"Payment History - Modified on {self.modification_date}"

@receiver(post_save, sender=Payment)
def update_project_payment_status(sender, instance, **kwargs):
    """
    Actualiza el estado de pago del proyecto cuando se guarda un pago.
    """
    instance.project.update_payment_status()
    