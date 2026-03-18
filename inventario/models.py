from django.db import models
from django.utils import timezone
from django.db.models import Sum

from projects.models import AuditModel, Proyecto


class Proveedor(AuditModel):
    nombre    = models.CharField(max_length=200, verbose_name="Nombre")
    rubro     = models.CharField(max_length=100, verbose_name="Rubro")
    celular   = models.CharField(max_length=15, verbose_name="Celular")
    correo    = models.EmailField(max_length=100, blank=True, verbose_name="Correo Electrónico")
    direccion = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    nit       = models.CharField(max_length=20, blank=True, verbose_name="NIT")

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']
        db_table = 'projects_proveedor'

    def __str__(self):
        return self.nombre


class Insumo(AuditModel):
    CATEGORIA_CHOICES = [
        ('camara_ip',        'Cámara IP'),
        ('camara_analogica', 'Cámara Analógica'),
        ('nvr_dvr',          'NVR / DVR'),
        ('alarma',           'Sistema de Alarma'),
        ('sensor',           'Sensor'),
        ('cable',            'Cable'),
        ('fuente',           'Fuente de Alimentación'),
        ('pantalla',         'Pantalla / Display'),
        ('computadora',      'Equipo Computacional'),
        ('red',              'Equipo de Red'),
        ('accesorio',        'Accesorio'),
    ]
    nombre         = models.CharField(max_length=200, verbose_name="Nombre")
    marca          = models.CharField(max_length=100, verbose_name="Marca")
    categoria      = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, verbose_name="Categoría")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Bs.)")
    stock          = models.IntegerField(default=0, verbose_name="Stock actual")
    stock_minimo   = models.PositiveIntegerField(default=0, verbose_name="Stock mínimo de alerta")

    def recalculate_stock(self):
        compras   = self.compras.filter(activo=True).aggregate(t=Sum('cantidad'))['t'] or 0
        asignados = self.proyectos.aggregate(t=Sum('cantidad'))['t'] or 0
        self.stock = compras - asignados
        self.save(update_fields=['stock'])

    @property
    def stock_status(self):
        if self.stock <= 0:
            return 'agotado'
        if self.stock_minimo > 0 and self.stock <= self.stock_minimo:
            return 'bajo'
        return 'ok'

    class Meta:
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'
        ordering = ['categoria', 'nombre']
        db_table = 'projects_insumo'

    def __str__(self):
        return f"{self.get_categoria_display()} — {self.nombre} ({self.marca})"


class Requiere(models.Model):
    proyecto       = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='insumos', verbose_name="Proyecto")
    insumo         = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='proyectos', verbose_name="Insumo")
    cantidad       = models.PositiveIntegerField(verbose_name="Cantidad")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Bs.)")
    created        = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Insumo del Proyecto'
        verbose_name_plural = 'Insumos del Proyecto'
        ordering = ['-created']
        unique_together = [('proyecto', 'insumo')]
        db_table = 'projects_requiere'

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.insumo.nombre} x{self.cantidad} → {self.proyecto.nombre}"


class Realizar(AuditModel):
    proveedor      = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='compras', verbose_name="Proveedor")
    insumo         = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='compras', verbose_name="Insumo")
    cantidad       = models.PositiveIntegerField(verbose_name="Cantidad")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Bs.)")
    costo_total    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo Total (Bs.)")
    fecha          = models.DateField(verbose_name="Fecha de Compra")

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha']
        db_table = 'projects_realizar'

    def __str__(self):
        return f"{self.insumo.nombre} x{self.cantidad} de {self.proveedor.nombre} ({self.fecha})"
