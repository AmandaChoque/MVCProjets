from django.db import models
from django.db.models import Q, Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from projects.models import AuditModel, Proyecto


class Proveedor(AuditModel):
    RUBRO_CHOICES = [
        ('camaras_seguridad',   'Cámaras y Equipos de Seguridad'),
        ('cables_conectores',   'Cables y Conectores'),
        ('equipos_red',         'Equipos de Red'),
        ('alarmas_perifoneo',   'Alarmas, Perifoneo y GSM'),
        ('sensores',            'Sensores'),
        ('computo',             'Equipos de Cómputo'),
        ('distribuidor',        'Distribuidor General'),
        ('otro',                'Otro'),
    ]

    # ── Datos de la empresa ──────────────────────────────────────────────────
    nombre    = models.CharField(max_length=200, verbose_name="Razón Social / Nombre de la Empresa")
    rubro     = models.CharField(max_length=30, choices=RUBRO_CHOICES, verbose_name="Rubro")
    nit       = models.CharField(max_length=20, blank=True, verbose_name="NIT")
    telefono  = models.CharField(max_length=15, verbose_name="Teléfono de la Empresa")
    correo    = models.EmailField(max_length=100, blank=True, verbose_name="Correo de la Empresa")
    direccion = models.CharField(max_length=255, blank=True, verbose_name="Dirección")

    # ── Encargado / Contacto (opcional) ──────────────────────────────────────
    encargado_nombre  = models.CharField(max_length=150, blank=True, default='', verbose_name="Nombre del Encargado")
    encargado_cargo   = models.CharField(max_length=100, blank=True, default='', verbose_name="Cargo del Encargado")
    encargado_celular = models.CharField(max_length=15,  blank=True, default='', verbose_name="Celular del Encargado")
    encargado_correo  = models.EmailField(blank=True,    default='', verbose_name="Correo del Encargado")

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']
        db_table = 'inventario_proveedor'
        constraints = [
            models.UniqueConstraint(
                fields=['nit'],
                condition=~Q(nit=''),
                name='unique_proveedor_nit_when_not_empty',
            )
        ]

    def __str__(self):
        return self.nombre


class Insumo(AuditModel):
    CATEGORIA_CHOICES = [
        ('camara_ip',        'Cámara IP'),
        ('camara_analogica', 'Cámara Analógica'),
        ('nvr_dvr',          'NVR / DVR'),
        ('alarma_sonora',    'Alarma Sonora'),
        ('alarma_gsm',       'Alarma GSM (activable por llamada)'),
        ('perifoneo',        'Sistema de Perifoneo'),
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
    modelo         = models.CharField(max_length=100, blank=True, default='', verbose_name="Modelo")
    categoria      = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, verbose_name="Categoría")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Costo Unitario (Bs.)")
    # Desnormalización controlada: calculado desde compras - asignados.
    # Mantenido automáticamente por señales. Nunca modificar directamente.
    stock          = models.IntegerField(default=0, verbose_name="Stock actual")
    stock_minimo   = models.PositiveIntegerField(default=5, verbose_name="Stock mínimo de alerta")

    def _recalculate_stock(self):
        """Uso exclusivo de señales — no llamar desde vistas ni formularios."""
        compras   = self.compras.filter(activo=True).aggregate(t=Sum('cantidad'))['t'] or 0
        asignados = self.proyectos.filter(activo=True).aggregate(t=Sum('cantidad'))['t'] or 0
        self.stock = compras - asignados
        self.save(update_fields=['stock'])

    @property
    def costo_promedio(self):
        """Costo promedio ponderado calculado desde las compras activas."""
        compras = self.compras.filter(activo=True)
        total_cantidad = compras.aggregate(t=Sum('cantidad'))['t'] or 0
        if total_cantidad == 0:
            return self.costo_unitario or Decimal('0')
        total_costo = sum(c.cantidad * c.costo_unitario for c in compras)
        return round(total_costo / total_cantidad, 2)

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
        db_table = 'inventario_insumo'
        constraints = [
            models.UniqueConstraint(
                fields=['nombre', 'marca', 'modelo'],
                condition=Q(activo=True),
                name='unique_insumo_nombre_marca_modelo',
            ),
            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='insumo_stock_no_negativo',
            ),
        ]

    def __str__(self):
        return f"{self.get_categoria_display()} — {self.nombre} ({self.marca})"


class Requiere(AuditModel):
    proyecto       = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='insumos', verbose_name="Proyecto")
    insumo         = models.ForeignKey(Insumo, on_delete=models.SET_NULL, null=True, related_name='proyectos', verbose_name="Insumo")
    cantidad       = models.PositiveIntegerField(verbose_name="Cantidad")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Bs.)")

    class Meta:
        verbose_name = 'Insumo del Proyecto'
        verbose_name_plural = 'Insumos del Proyecto'
        ordering = ['-created']
        db_table = 'inventario_requiere'
        constraints = [
            # Solo un insumo activo por proyecto — los soft-deleted no bloquean la reasignación
            models.UniqueConstraint(
                fields=['proyecto', 'insumo'],
                condition=Q(activo=True),
                name='unique_requiere_proyecto_insumo_activo',
            )
        ]

    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        insumo = self.insumo.nombre if self.insumo else 'Insumo eliminado'
        return f"{insumo} x{self.cantidad} → {self.proyecto.nombre}"


class Compra(AuditModel):
    # FK con SET_NULL para preservar el historial si se elimina el proveedor o insumo
    proveedor      = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, related_name='compras', verbose_name="Proveedor")
    insumo         = models.ForeignKey(Insumo, on_delete=models.SET_NULL, null=True, related_name='compras', verbose_name="Insumo")
    cantidad       = models.PositiveIntegerField(verbose_name="Cantidad")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Bs.)")
    costo_total    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo Total (Bs.)")
    fecha          = models.DateField(verbose_name="Fecha de Compra")

    def save(self, *args, **kwargs):
        # Desnormalización controlada: costo_total se deriva de cantidad × costo_unitario.
        # Se recalcula aquí para que la BD nunca tenga valores inconsistentes.
        self.costo_total = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha']
        db_table = 'inventario_compra'

    def __str__(self):
        insumo    = self.insumo.nombre    if self.insumo    else 'Insumo eliminado'
        proveedor = self.proveedor.nombre if self.proveedor else 'Proveedor eliminado'
        return f"{insumo} x{self.cantidad} de {proveedor} ({self.fecha})"


# ── Alias para compatibilidad (se puede eliminar cuando todas las referencias sean Compra) ──
Realizar = Compra


# ── Señales: recalcular stock automáticamente ─────────────────────────────────

@receiver(post_save, sender=Compra)
@receiver(post_delete, sender=Compra)
def compra_recalculate_stock(sender, instance, **kwargs):
    if instance.insumo is None:
        return
    insumo = instance.insumo
    insumo._recalculate_stock()
    # Actualizar costo_unitario al último precio de compra registrado
    ultima_compra = Compra.objects.filter(insumo=insumo, activo=True).order_by('-fecha', '-created').first()
    if ultima_compra:
        Insumo.objects.filter(pk=insumo.pk).update(costo_unitario=ultima_compra.costo_unitario)


@receiver(post_save, sender=Requiere)
@receiver(post_delete, sender=Requiere)
def requiere_recalculate_stock(sender, instance, **kwargs):
    if instance.insumo is None:
        return
    instance.insumo._recalculate_stock()
