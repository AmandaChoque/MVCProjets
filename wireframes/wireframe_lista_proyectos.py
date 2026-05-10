import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

# Colores reales del sistema SOBOTEC
AZUL_DARK  = '#0F2D5A'
AZUL       = '#1B4D90'
DORADO     = '#D4B84A'
DORADO_LUZ = '#F0D878'
BG         = '#f1f3f6'
VERDE_SEC  = '#7bd9a5'
AZUL_SEC   = '#93c5fd'

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')
fig.patch.set_facecolor('white')

# ─── Helpers ────────────────────────────────────────────────────────────────

def rect(x, y, w, h, fc='white', ec='#ccc', lw=1.0):
    ax.add_patch(patches.Rectangle(
        (x, y), w, h, linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))

def rounded(x, y, w, h, fc='white', ec='#ccc', lw=1.0, pad=0.05):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad={pad}",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=3))

def t(x, y, s, size=8, bold=False, ha='left', va='center',
      color='black', italic=False):
    ax.text(x, y, s, fontsize=size,
            fontweight='bold' if bold else 'normal',
            fontstyle='italic' if italic else 'normal',
            ha=ha, va=va, color=color, zorder=4)

def hline(x0, x1, y, color='#ddd', lw=0.5):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, zorder=3)

def badge(x, y, w, h, label, fc, tc='white', size=6.8):
    rounded(x, y, w, h, fc=fc, ec='none', lw=0, pad=0.03)
    t(x + w/2, y + h/2, label, size=size, bold=True, ha='center', color=tc)

def btn(x, y, w, h, label, fc, tc='white', size=7.5, ec='none'):
    rounded(x, y, w, h, fc=fc, ec=ec, lw=0.8, pad=0.04)
    t(x + w/2, y + h/2, label, size=size, bold=True, ha='center', color=tc)

def input_field(x, y, w, h, placeholder='', value='', select=False):
    rounded(x, y, w, h, fc='white', ec='#bbb', lw=0.7, pad=0.03)
    if select:
        t(x + 0.1, y + h/2, value or 'Todos', size=7, color='#555')
        t(x + w - 0.18, y + h/2, '▾', size=7, ha='center', color='#888')
    elif placeholder:
        t(x + 0.1, y + h/2, placeholder, size=6.8, color='#bbb')

# ════════════════════════════════════════════════════════════════════════════
# NAVBAR  (y = 9.35 → 10.0)
# ════════════════════════════════════════════════════════════════════════════
rect(0, 9.35, 14, 0.65, fc=AZUL, ec=AZUL_DARK, lw=0)

rounded(0.15, 9.44, 0.42, 0.42, fc='#ffffff22', ec='#ffffff44', lw=0.5, pad=0.02)
t(0.36, 9.65, '▣', size=10, ha='center', color='white')
t(0.68, 9.68, 'SOBOTEC S.R.L.', size=12, bold=True, color=DORADO)

rounded(12.0, 9.47, 0.46, 0.34, fc='none', ec='#ffffff66', lw=0.7, pad=0.02)
t(12.23, 9.64, '🔔', size=9, ha='center', color='white')
rounded(12.58, 9.47, 1.28, 0.34, fc='none', ec='#ffffff66', lw=0.7, pad=0.02)
t(13.22, 9.64, 'usuario ▾', size=8, ha='center', color='white')

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR  (x = 0→2.75,  y = 0→9.35)
# ════════════════════════════════════════════════════════════════════════════
rect(0, 0, 2.75, 9.35, fc=AZUL, ec=AZUL_DARK, lw=0)

def sidebar_section(y, label, color):
    hline(0.1, 2.65, y + 0.04, color='#ffffff22', lw=0.6)
    t(0.18, y - 0.1, label.upper(), size=6, bold=True, color=color)

def sidebar_item(y, icon, label, active=False, indent=False):
    ix = 0.35 if not indent else 0.55
    if active:
        rect(0.05, y - 0.18, 2.65, 0.36, fc='#D4B84A33', ec='none', lw=0)
        ax.plot([0.05, 0.05], [y - 0.18, y + 0.18],
                color=DORADO, linewidth=2.5, zorder=5)
        color = DORADO_LUZ
    else:
        color = '#ffffffcc'
    t(ix, y, f'{icon}  {label}',
      size=7.5 if not indent else 7.0,
      color=color, bold=active)

sidebar_section(9.1,  '⬛ Proyectos', DORADO)
sidebar_item(8.75, '👤', 'Clientes')
sidebar_item(8.35, '📁', 'Proyectos  ▾', active=True)
sidebar_item(7.92, '▸', 'Listar',        active=True, indent=True)
sidebar_item(7.52, '▸', 'Reporte',       indent=True)
sidebar_item(7.12, '▸', 'Análisis',      indent=True)
sidebar_item(6.72, '💰', 'Pagos Proyectos  ▾')

sidebar_section(6.28, '👥 Personal', AZUL_SEC)
sidebar_item(5.92, '👥', 'Empleados  ▾')
sidebar_item(5.52, '💳', 'Pagos a Empleados')
sidebar_item(5.12, '📋', 'Plantillas de Tareas')

sidebar_section(4.68, '📦 Inventario', VERDE_SEC)
sidebar_item(4.32, '📦', 'Insumos  ▾')
sidebar_item(3.92, '🛒', 'Compras')
sidebar_item(3.52, '🚚', 'Proveedores')

# ════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT  (x = 2.9→13.9,  y = 0→9.35)
# ════════════════════════════════════════════════════════════════════════════
MX = 2.9
MW = 10.9
rect(MX, 0, MW, 9.35, fc=BG, ec='none', lw=0)

# ── Título + botón Nuevo ─────────────────────────────────────────────────────
t(MX + 0.15, 9.0, 'Gestión de Proyectos', size=12, bold=True, color=AZUL)
btn(12.1, 8.82, 1.65, 0.38, '+ Nuevo Proyecto', fc=AZUL, size=8)

# ── Fila: Mostrar / contador ─────────────────────────────────────────────────
t(MX + 0.15, 8.48, 'Mostrar:', size=8, color='#666')
input_field(MX + 0.95, 8.32, 0.75, 0.28, select=True, value='10')
t(13.75, 8.48, 'Mostrando 1 – 10 de 12 registros',
  size=7.5, ha='right', color='#888')

# ── Card de filtros — FILA 1: nombre + estado + tipo + pago ─────────────────
rect(MX, 7.25, MW, 1.0, fc='white', ec='#ddd', lw=0.8)

# Etiquetas fila 1
labels_f1 = ['Nombre del proyecto', 'Estado', 'Tipo', 'Estado de pago']
widths_f1  = [2.8, 1.7, 1.7, 1.7]
fx = MX + 0.18
for lbl, fw in zip(labels_f1, widths_f1):
    t(fx, 8.12, lbl, size=7, color='#777')
    fx += fw + 0.16

# Inputs fila 1
fx = MX + 0.18
input_field(fx, 7.82, 2.8, 0.26, placeholder='Buscar por nombre...')
fx += 2.8 + 0.16
for fw in [1.7, 1.7, 1.7]:
    input_field(fx, 7.82, fw, 0.26, select=True)
    fx += fw + 0.16

# Botones Filtrar / Limpiar al final de fila 1
btn(fx, 7.82, 1.0, 0.26, 'Filtrar',  fc='#212529', size=7.5)
btn(fx + 1.1, 7.82, 0.85, 0.26, 'Limpiar', fc='white', tc='#555', size=7.5, ec='#bbb')

# Etiquetas fila 2: fechas
labels_f2 = ['Inicio desde', 'Inicio hasta', 'Fin desde', 'Fin hasta']
widths_f2  = [2.1, 2.1, 2.1, 2.1]
fx2 = MX + 0.18
for lbl, fw in zip(labels_f2, widths_f2):
    t(fx2, 7.62, lbl, size=7, color='#777')
    input_field(fx2, 7.32, fw, 0.26, placeholder='dd/mm/aaaa')
    fx2 += fw + 0.16

# ── Tabla ────────────────────────────────────────────────────────────────────
# Cabecera
rect(MX, 6.76, MW, 0.4, fc='#e9ecef', ec='#dee2e6', lw=0.8)
cols  = ['Código', 'Nombre del Proyecto', 'Contratante', 'Tipo',
         'Estado', 'Estado Pago', 'Monto (Bs.)', 'Acc.']
col_x = [MX+0.12, MX+0.95, MX+3.3, MX+5.3, MX+6.55,
         MX+7.75,  MX+9.05, MX+10.4]
for cx, col in zip(col_x, cols):
    t(cx, 6.96, col.upper(), size=6.5, bold=True, color='#555')

# Filas
filas = [
    ('PR-001', 'Seg. Edificio Central', 'Juan Pérez',   'Instalación',  'En Progreso', 'Parcial',   '18,500.00'),
    ('PR-002', 'CCTV Almacén Norte',    'Ana Flores',   'Mantenimiento','Completado',  'Pagado',    ' 9,200.00'),
    ('PR-003', 'Alarmas Oficina Sur',   'Carlos Mamani','Instalación',  'Pendiente',   'No Pagado', '12,000.00'),
    ('PR-004', 'DVR Sucursal Este',     'Luis Quispe',  'Instalación',  'En Progreso', 'Parcial',   ' 7,800.00'),
    ('PR-005', 'Cámaras IP Centro',     'María García', 'Instalación',  'Completado',  'Pagado',    '15,400.00'),
]
estado_colors = {'En Progreso': '#0d6efd', 'Completado': '#198754', 'Pendiente': '#ffc107'}
pago_colors   = {'Pagado': '#198754', 'Parcial': '#0dcaf0', 'No Pagado': '#dc3545'}
pago_tc       = {'Pagado': 'white',   'Parcial': '#111',    'No Pagado': 'white'}

for i, (cod, nom, cont, tipo, est, pago, monto) in enumerate(filas):
    yr = 6.33 - i * 0.46
    fc_row = 'white' if i % 2 == 0 else '#f8f9fa'
    rect(MX, yr - 0.2, MW, 0.44, fc=fc_row, ec='#dee2e6', lw=0.4)
    t(col_x[0], yr, cod,   size=7.5, color='#888')
    t(col_x[1], yr, nom,   size=7.5, bold=True, color='#222')
    t(col_x[2], yr, cont,  size=7.5, color='#444')
    badge(col_x[3]-0.05, yr-0.14, 1.1, 0.28, tipo,   fc='#6c757d', size=6.5)
    badge(col_x[4]-0.05, yr-0.14, 1.1, 0.28, est,
          fc=estado_colors[est], tc='white' if est != 'Pendiente' else '#111', size=6.5)
    badge(col_x[5]-0.05, yr-0.14, 1.1, 0.28, pago,
          fc=pago_colors[pago], tc=pago_tc[pago], size=6.5)
    t(col_x[6], yr, monto, size=7.5, bold=True, color='#333')
    rounded(col_x[7]-0.02, yr-0.14, 0.42, 0.28,
            fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(col_x[7]+0.19, yr, '⋮', size=10, ha='center', color='#555')

# Borde exterior tabla
rect(MX, 4.03, MW, 3.13, fc='none', ec='#dee2e6', lw=1.0)

# ── Paginación ────────────────────────────────────────────────────────────────
pag = [('Anterior', 1.0), ('1', 0.38), ('2', 0.38), ('3', 0.38), ('Siguiente', 1.0)]
px = 5.8
for lbl, w in pag:
    activo = lbl == '1'
    rounded(px, 3.72, w, 0.32, fc=AZUL if activo else 'white',
            ec='#dee2e6', lw=0.8, pad=0.03)
    t(px + w/2, 3.88, lbl, size=7.5, ha='center',
      color='white' if activo else '#555', bold=activo)
    px += w + 0.06

# ─── Caption ──────────────────────────────────────────────────────────────────
t(7.0, 0.3, 'Figura XX: Lista de Proyectos — Sistema SOBOTEC S.R.L.',
  size=9, ha='center', italic=True, color='#555')

# Marco exterior
rect(0, 0, 14, 10, fc='none', ec='#999', lw=1.5)

plt.tight_layout(pad=0)
plt.savefig('wireframes/wireframe_lista_proyectos.png',
            dpi=160, bbox_inches='tight', facecolor='white')
plt.show()
print("Guardado: wireframes/wireframe_lista_proyectos.png")
