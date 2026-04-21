"""
Genera diagrama navegacional UML del sistema SOBOTEC S.R.L.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def rbox(ax, x, y, w, h, fc, ec='none', lw=1.5, zorder=2, pad=0.08):
    """Rectángulo redondeado."""
    p = FancyBboxPatch(
        (x + pad, y + pad),
        max(w - 2*pad, 0.05),
        max(h - 2*pad, 0.05),
        boxstyle=f"round,pad={pad}",
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
        zorder=zorder,
        clip_on=False,
    )
    ax.add_patch(p)
    return p


def shadow_box(ax, x, y, w, h, zorder=1):
    rbox(ax, x + 0.12, y - 0.12, w, h, fc='#00000018', ec='none', lw=0, zorder=zorder, pad=0.1)


def module_box(ax, x, y, w, h, hdr_color, title, items,
               hdr_h=0.78, icon='', fsize=7.8):
    """
    Caja de módulo con cabecera coloreada y cuerpo blanco listando páginas.
    Líneas que empiezan con '§' se tratan como separadores de sección.
    """
    body_h = h - hdr_h

    # Sombra
    shadow_box(ax, x, y, w, h)

    # Cuerpo blanco
    rbox(ax, x, y, w, body_h, fc='#FAFBFC', ec=hdr_color, lw=1.6, zorder=2, pad=0.06)

    # Cabecera (encima del cuerpo para tapar la esquina superior del borde)
    rbox(ax, x, y + body_h, w, hdr_h, fc=hdr_color, ec='none', lw=0, zorder=3, pad=0.06)

    # Título de cabecera
    label = f'{icon}  {title}' if icon else title
    ax.text(x + w/2, y + body_h + hdr_h/2, label,
            ha='center', va='center', fontsize=10.5,
            color='white', fontweight='bold', zorder=4, clip_on=False)

    # Items
    n = len(items)
    if n == 0:
        return
    usable = body_h - 0.22
    step = usable / (n + 0.3)
    for i, item in enumerate(items):
        iy = y + body_h - 0.16 - (i + 0.5) * step
        if item.startswith('§'):
            # Línea separadora con etiqueta centrada
            label_sep = item[1:].strip()
            lx0, lx1 = x + 0.15, x + w - 0.15
            ax.plot([lx0, lx1], [iy, iy],
                    color=hdr_color, lw=0.9, alpha=0.45, zorder=4)
            if label_sep:
                ax.text(x + w/2, iy + step * 0.32, label_sep,
                        ha='center', va='center', fontsize=6.4,
                        color=hdr_color, fontstyle='italic',
                        fontweight='bold', zorder=4, clip_on=False)
        else:
            ax.text(x + 0.22, iy, item,
                    ha='left', va='center', fontsize=fsize,
                    color='#1A1A2E', zorder=4, clip_on=False,
                    fontfamily='monospace')


def node(ax, x, y, w, h, fc, text, fsize=9.0, zorder=3):
    """Nodo simple (Auth / Dashboard)."""
    shadow_box(ax, x, y, w, h, zorder=zorder-1)
    rbox(ax, x, y, w, h, fc=fc, ec='none', lw=0, zorder=zorder, pad=0.1)
    ax.text(x + w/2, y + h/2, text,
            ha='center', va='center', fontsize=fsize,
            color='white', fontweight='bold', zorder=zorder+1, clip_on=False,
            multialignment='center')


def arr(ax, x1, y1, x2, y2, color='#546E7A', lw=2.0, zorder=6, rad=0.0):
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle='->', color=color, lw=lw,
            connectionstyle=f'arc3,rad={rad}',
        ),
        zorder=zorder,
    )


# ─────────────────────────────────────────────
# Figura
# ─────────────────────────────────────────────
W, H = 25, 34
fig = plt.figure(figsize=(W, H), dpi=130)
ax = fig.add_axes([0.012, 0.01, 0.976, 0.98])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
fig.patch.set_facecolor('#E9EEF4')
ax.set_facecolor('#E9EEF4')

# Paleta
C = dict(
    nav       = '#1A237E',
    proyectos = '#1B5E20',
    clientes  = '#0D47A1',
    plantillas= '#4A148C',
    pagos_p   = '#880E4F',
    empleados = '#004D40',
    inventario= '#BF360C',
    notif     = '#37474F',
    dash      = '#1565C0',
)

# ─────────────────────────────────────────────
# BARRA TÍTULO
# ─────────────────────────────────────────────
rbox(ax, 0, H-1.8, W, 1.8, fc=C['nav'], ec='none', lw=0, zorder=2, pad=0)
ax.text(W/2, H-0.82, 'SOBOTEC S.R.L.  ·  Sistema de Gestión de Proyectos de Seguridad',
        ha='center', va='center', fontsize=15.5,
        color='white', fontweight='bold', zorder=3)
ax.text(W/2, H-1.42, 'Diagrama de Navegación  —  UML',
        ha='center', va='center', fontsize=10,
        color='#90CAF9', zorder=3)

# ─────────────────────────────────────────────
# FILA AUTH  (y=29.5 – 31.5)
# ─────────────────────────────────────────────
node(ax, 0.4, 29.6, 3.6, 1.5, C['nav'],
     '« page »\n🌐  Landing\n/', fsize=8.5)

module_box(ax, 4.6, 29.4, 5.8, 1.9, C['nav'], 'Autenticación', [
    '/signin/  · Iniciar sesión',
    '/signup/  · Registrarse',
    '/cambiar-contrasena/',
], hdr_h=0.65, icon='🔐', fsize=8.2)

node(ax, 11.1, 29.6, 5.8, 1.5, C['dash'],
     '« page »\n🏠  Dashboard\n/dashboard/', fsize=8.8)

module_box(ax, 17.6, 29.4, 6.9, 1.9, C['notif'], 'Notificaciones', [
    '/notificaciones/  · Lista',
    '/notificaciones/{id}/leer/',
    '/notificaciones/leer-todas/',
], hdr_h=0.65, icon='🔔', fsize=8.2)

# Flechas auth
arr(ax, 4.0,  30.35, 4.6,  30.35, color=C['nav'])
arr(ax, 10.4, 30.35, 11.1, 30.35, color=C['nav'])
arr(ax, 16.9, 30.35, 17.6, 30.35, color=C['notif'])

# ─────────────────────────────────────────────
# COLUMNA IZQUIERDA: PROYECTOS (x=0.4, w=8)
# ─────────────────────────────────────────────
proj_items = [
    '/proyectos/  · Lista y filtros',
    '/proyectos/nuevo/  · Crear proyecto',
    '/proyectos/{id}/  · Detalle / Editar',
    '/proyectos/{id}/ver/  · Vista completa',
    '/proyectos/analisis/  · Análisis',
    '/proyectos/reporte/  · Reporte PDF',
    '§ Sedes de Instalación',
    '/proyectos/{id}/sedes/nueva/',
    '/sedes/{id}/  · Detalle / Editar',
    '/sedes/{id}/ver/  · Checklist + Fotos',
    '   ↳ tareas: crear / editar / toggle',
    '   ↳ reordenar / aplicar plantilla',
    '   ↳ fotos: subir / eliminar',
    '§ Equipo del Proyecto',
    '/proyectos/{id}/equipo/agregar/',
    '/proyectos/{id}/equipo/{id}/remover/',
    '§ Contrato de Proyecto',
    '/proyectos/{id}/contrato-proyecto/nuevo/',
    '/contratos/proyecto/{id}/  · Detalle',
    '/contratos/proyecto/{id}/desactivar/',
    '§ Insumos del Proyecto',
    '/proyectos/{id}/insumos/nuevo/',
    '/insumos-proyecto/{id}/  · Detalle',
    '/insumos-proyecto/{id}/qr/  · QR',
    '§ Jornadas',
    '/proyectos/{id}/jornadas/revision/',
]
module_box(ax, 0.4, 1.4, 8.0, 27.8, C['proyectos'], 'Proyectos',
           proj_items, hdr_h=0.78, icon='📁', fsize=7.7)

# Dashboard → Proyectos
arr(ax, 12.0, 29.6, 4.4, 29.2, color=C['proyectos'], lw=2.2, rad=-0.1)

# ─────────────────────────────────────────────
# COLUMNA CENTRAL: CLIENTES + PLANTILLAS + PAGOS (x=9.1, w=7.2)
# ─────────────────────────────────────────────
clientes_items = [
    '/clientes/  · Lista + búsqueda',
    '/clientes/nuevo/  · Crear cliente',
    '/clientes/{id}/  · Detalle / Editar',
    '/clientes/{id}/ver/  · Vista',
]
module_box(ax, 9.1, 21.8, 7.2, 7.2, C['clientes'], 'Clientes',
           clientes_items, hdr_h=0.78, icon='👤', fsize=8.0)

plantillas_items = [
    '/plantillas/  · Lista',
    '/plantillas/nueva/  · Crear',
    '/plantillas/{id}/  · Detalle',
    '§ Ítems de plantilla',
    '/plantillas/{id}/items/nuevo/',
    '/plantillas/items/{id}/editar/',
    '/plantillas/items/{id}/eliminar/',
    '/plantillas/{id}/items/reordenar/',
]
module_box(ax, 9.1, 12.0, 7.2, 9.4, C['plantillas'], 'Plantillas de Tareas',
           plantillas_items, hdr_h=0.78, icon='📋', fsize=8.0)

pagos_p_items = [
    '/pagos/  · Lista de pagos',
    '/pagos/nuevo/  · Registrar pago',
    '/pagos/{id}/  · Detalle / Editar',
    '/pagos/{id}/ver/  · Vista',
    '/pagos/analisis/  · Análisis',
    '/pagos/filtrar/  · Filtro AJAX',
]
module_box(ax, 9.1, 1.4, 7.2, 10.2, C['pagos_p'], 'Pagos al Proyecto',
           pagos_p_items, hdr_h=0.78, icon='💰', fsize=8.0)

# Dashboard → columna central
arr(ax, 14.0, 29.6, 12.7, 29.0, color=C['clientes'], lw=2.2, rad=0.05)

# ─────────────────────────────────────────────
# COLUMNA DERECHA: EMPLEADOS + INVENTARIO (x=17.0, w=7.6)
# ─────────────────────────────────────────────
emp_items = [
    '/empleados/  · Lista',
    '/empleados/nuevo/  · Crear',
    '/empleados/{id}/  · Detalle / Editar',
    '/empleados/{id}/ver/  · Vista',
    '/empleados/carga/  · Carga laboral',
    '/empleados/reporte/  · Reporte PDF',
    '/mi-trabajo/  · Dashboard instalador',
    '§ Contratos de Empleado',
    '/empleados/{id}/contratos/nuevo/',
    '/contratos/empleado/{id}/  · Detalle',
    '/contratos/empleado/{id}/pdf/  · PDF',
    '§ Jornadas',
    '/contratos/empleado/{id}/jornadas/nueva/',
    '/jornadas/{id}/  · Detalle',
    '   ↳ aprobar / rechazar jornada',
    '§ Pagos a Empleados',
    '/pagos-empleados/  · Lista',
    '/contratos/empleado/{id}/pagos/nuevo/',
    '/pagos-empleado/{id}/  · Detalle',
]
module_box(ax, 17.0, 13.2, 7.6, 16.0, C['empleados'], 'Empleados',
           emp_items, hdr_h=0.78, icon='👷', fsize=7.7)

inv_items = [
    '§ Proveedores',
    '/proveedores/  · Lista',
    '/proveedores/nuevo/  · Crear',
    '/proveedores/{id}/  · Detalle',
    '§ Insumos / Stock',
    '/insumos/  · Lista + stock',
    '/insumos/nuevo/  · Crear',
    '/insumos/{id}/  · Detalle',
    '/insumos/{id}/ver/  · Vista + compras',
    '§ Compras a Proveedores',
    '/compras/  · Lista',
    '/compras/nueva/  · Nueva compra',
    '/compras/{id}/  · Detalle',
    '/inventario/reporte/  · Reporte PDF',
]
module_box(ax, 17.0, 1.4, 7.6, 11.4, C['inventario'], 'Inventario',
           inv_items, hdr_h=0.78, icon='📦', fsize=7.7)

# Dashboard → columna derecha
arr(ax, 16.2, 29.6, 20.8, 29.2, color=C['empleados'], lw=2.2, rad=0.1)

# ─────────────────────────────────────────────
# LEYENDA INFERIOR
# ─────────────────────────────────────────────
rbox(ax, 0.4, 0.08, W-0.8, 1.1, fc='white', ec='#B0BEC5', lw=1, zorder=2, pad=0.05)
ax.text(0.85, 0.75, 'Módulos:', ha='left', va='center',
        fontsize=8.5, color='#37474F', fontweight='bold', zorder=3)

legend = [
    (C['nav'],        '🔐 Autenticación'),
    (C['proyectos'],  '📁 Proyectos'),
    (C['clientes'],   '👤 Clientes'),
    (C['plantillas'], '📋 Plantillas'),
    (C['pagos_p'],    '💰 Pagos proyecto'),
    (C['empleados'],  '👷 Empleados'),
    (C['inventario'], '📦 Inventario'),
    (C['notif'],      '🔔 Notificaciones'),
]
for i, (color, label) in enumerate(legend):
    lx = 2.5 + i * 2.85
    rbox(ax, lx, 0.38, 0.42, 0.42, fc=color, ec='none', lw=0, zorder=3, pad=0.03)
    ax.text(lx + 0.58, 0.62, label,
            ha='left', va='center', fontsize=7.8, color='#1A1A2E', zorder=3)

# ─────────────────────────────────────────────
# Guardar
# ─────────────────────────────────────────────
out = 'diagrama_navegacional.png'
plt.savefig(out, dpi=130, bbox_inches='tight',
            facecolor='#E9EEF4', edgecolor='none')
plt.close()
print(f'Guardado: {out}')
