"""
Genera wireframes con el layout REAL del sistema SOBOTEC:
- Navbar superior delgado (azul oscuro)
- Sidebar izquierdo (250px, azul oscuro, secciones con colores)
- Contenido a la derecha del sidebar
Salida: wireframes/wf_10_jornadas.png  y  wireframes/wf_11_compras.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

OUT = r"c:\Users\DELL\Desktop\taller II v1\MVCProjets\wireframes"

# ── Colores del sistema real ─────────────────────────────
AZ_DARK  = '#0F2D5A'   # sidebar / navbar fondo
AZ_MID   = '#1B4D90'   # sidebar gradiente claro
DORADO   = '#D4B84A'   # brand + sección proyectos
AZUL_SEC = '#93C5FD'   # sección personal
VERDE_SEC= '#7BD9A5'   # sección inventario
CONTENT_BG = '#F1F3F6' # fondo contenido
WHITE    = '#FFFFFF'
GRAY1    = '#333333'
GRAY2    = '#6C757D'
GRAY3    = '#DEE2E6'
GRAY4    = '#F8F9FA'
TBHEAD   = '#E9ECEF'
BLUE_BTN = '#1B4D90'
GREEN    = '#198754'
ORANGE   = '#FD7E14'
RED      = '#DC3545'
GRAY_BTN = '#6C757D'
TEAL_B   = '#D1ECF1'
TEAL_T   = '#0C5460'
WARN_B   = '#FFF3CD'
WARN_T   = '#856404'

# ── Proporciones de layout ───────────────────────────────
NB_H  = 0.065   # altura navbar (fracción de figura)
SB_W  = 0.175   # ancho sidebar
# Área de contenido: x desde SB_W, y hasta 1-NB_H

def new_fig():
    fig, ax = plt.subplots(figsize=(14, 9.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(CONTENT_BG)
    return fig, ax

def r(ax, x, y, w, h, fc=WHITE, ec=GRAY3, lw=0.6, z=2, rad=0.002):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={rad}",
                       fc=fc, ec=ec, lw=lw, zorder=z,
                       transform=ax.transAxes, clip_on=False)
    ax.add_patch(p)

def t(ax, x, y, s, sz=7, color=GRAY1, bold=False, ha='left', va='center', z=3):
    ax.text(x, y, s, transform=ax.transAxes,
            fontsize=sz, color=color,
            fontweight='bold' if bold else 'normal',
            ha=ha, va=va, zorder=z, clip_on=False)

def btn(ax, x, y, w, h, label, fc=BLUE_BTN, sz=6.5):
    r(ax, x, y, w, h, fc=fc, ec=fc, lw=0, rad=0.003)
    t(ax, x+w/2, y+h/2, label, sz=sz, color=WHITE, bold=True, ha='center')

def badge(ax, x, y, w, h, label, fc=GREEN):
    r(ax, x, y, w, h, fc=fc, ec=fc, lw=0, rad=0.003)
    t(ax, x+w/2, y+h/2, label, sz=6, color=WHITE, bold=True, ha='center')

def inp(ax, x, y, w, h, ph):
    r(ax, x, y, w, h, fc=WHITE, ec=GRAY3)
    t(ax, x+0.008, y+h/2, ph, sz=6, color='#AAAAAA')

def sel(ax, x, y, w, h, label):
    r(ax, x, y, w, h, fc=WHITE, ec=GRAY3)
    t(ax, x+0.008, y+h/2, label, sz=6, color=GRAY1)
    t(ax, x+w-0.010, y+h/2, '▾', sz=6, color=GRAY2)

def vline(ax, x, y0, y1):
    ax.plot([x, x], [y0, y1], color=GRAY3, lw=0.4,
            transform=ax.transAxes, zorder=3)

# ── Navbar superior ──────────────────────────────────────
def navbar(ax):
    top = 1.0
    # fondo navbar
    r(ax, 0, top-NB_H, 1, NB_H, fc=AZ_DARK, ec=AZ_DARK, lw=0, z=10)
    # hamburger (3 líneas) al inicio
    hx, hy = 0.015, top - NB_H/2
    for dy in [-0.012, 0, 0.012]:
        ax.plot([hx, hx+0.022], [hy+dy, hy+dy], color=WHITE, lw=1.5,
                transform=ax.transAxes, zorder=11)
    # logo cuadrado dorado + texto brand
    r(ax, 0.050, top-NB_H+0.010, 0.030, 0.045, fc=DORADO, ec=DORADO, lw=0, z=11)
    t(ax, 0.088, top-NB_H/2, 'SOBOTEC S.R.L.', sz=10, color=DORADO, bold=True, z=11)
    # campana + usuario (derecha)
    t(ax, 0.88, top-NB_H/2, '🔔', sz=9, color=WHITE, z=11)
    t(ax, 0.918, top-NB_H/2, 'Administrador  ▾', sz=7, color='#ADB5BD', z=11)

# ── Sidebar ──────────────────────────────────────────────
def sidebar(ax, active_section='personal'):
    top = 1.0 - NB_H
    # fondo sidebar
    r(ax, 0, 0, SB_W, top, fc=AZ_DARK, ec=AZ_DARK, lw=0, z=5)

    sy = top - 0.018  # cursor vertical

    def section_label(text, color, icon=''):
        nonlocal sy
        # línea separadora sutil
        ax.plot([0.005, SB_W-0.005], [sy, sy], color='#FFFFFF22', lw=0.5,
                transform=ax.transAxes, zorder=6)
        sy -= 0.005
        t(ax, 0.012, sy, f'{icon}  {text}'.upper(), sz=5.5, color=color, bold=True, z=6)
        sy -= 0.022

    def nav_item(label, icon='•', active=False, indent=False):
        nonlocal sy
        h = 0.030
        ix = 0.008 if not indent else 0.022
        if active:
            r(ax, ix, sy-h, SB_W-ix-0.004, h, fc='#D4B84A33', ec=DORADO, lw=0.8, z=6)
        t(ax, ix+0.012, sy-h/2, f'{icon}  {label}', sz=6.5,
          color=DORADO if active else WHITE, bold=active, z=7)
        sy -= h + 0.003

    def nav_item_chevron(label, icon='•', expanded=False):
        nonlocal sy
        h = 0.030
        t(ax, 0.020, sy-h/2, f'{icon}  {label}', sz=6.5, color=WHITE, z=7)
        t(ax, SB_W-0.018, sy-h/2, '▾' if expanded else '›', sz=6, color='#AAAAAA', z=7)
        sy -= h + 0.003

    # ── PROYECTOS ──
    section_label('Proyectos', DORADO, '📁')
    nav_item('Clientes', '≡')
    nav_item_chevron('Proyectos', '📂', expanded=False)
    nav_item('Listar', '≡', indent=True)
    nav_item('Planificacion', '≡', indent=True)
    nav_item('Seguimiento', '≡', indent=True)
    nav_item('Rentabilidad', '≡', indent=True)
    nav_item_chevron('Pagos Proyectos', '💰', expanded=False)
    nav_item('Garantias', '🛡')

    # ── PERSONAL ──
    section_label('Personal', AZUL_SEC, '👥')
    nav_item_chevron('Empleados', '👤', expanded=True)
    nav_item('Listar', '≡', indent=True)
    nav_item('Gestion de jornadas', '≡', active=True, indent=True)
    nav_item('Reporte', '≡', indent=True)
    nav_item('Pagos a Empleados', '💳')

    # ── INVENTARIO ──
    section_label('Inventario', VERDE_SEC, '📦')
    nav_item_chevron('Insumos', '🔧', expanded=False)
    nav_item('Proveedores', '🚚')
    nav_item('Compras', '🛒')

# ── Helpers de contenido ─────────────────────────────────
CX = SB_W + 0.010   # inicio x del contenido
CW = 1 - SB_W - 0.015  # ancho disponible
CT = 1.0 - NB_H - 0.010  # top del contenido

def th(ax, x, y, w, h, cols, cw):
    r(ax, x, y, w, h, fc=TBHEAD, ec=GRAY3)
    cx = x
    for i, col in enumerate(cols):
        t(ax, cx+0.006, y+h/2, col, sz=6, color=GRAY1, bold=True)
        cx += cw[i]
        if i < len(cols)-1:
            vline(ax, cx, y, y+h)

def tr(ax, x, y0, rh, rows, cw, badge_col=None, bc_map=None):
    for ri, row in enumerate(rows):
        bg = WHITE if ri % 2 == 0 else GRAY4
        ry = y0 - ri * rh
        r(ax, x, ry-rh, sum(cw), rh, fc=bg, ec=GRAY3)
        cx = x
        for ci, cell in enumerate(row):
            if badge_col is not None and ci == badge_col:
                color = bc_map.get(cell, GRAY_BTN)
                badge(ax, cx+0.004, ry-rh+0.006, cw[ci]-0.010, rh-0.012, cell, fc=color)
            elif ci < len(row)-1:
                t(ax, cx+0.006, ry-rh/2, str(cell), sz=5.8, color=GRAY1)
            cx += cw[ci]
            if ci < len(row)-1:
                vline(ax, cx, ry-rh, ry)
    return y0 - len(rows)*rh

def pag(ax, x, y):
    t(ax, x, y+0.008, 'Mostrando 1-8 de 24', sz=6, color=GRAY2)
    bx = x + 0.19
    for i, lbl in enumerate(['‹','1','2','3','›']):
        fc = BLUE_BTN if lbl == '1' else WHITE
        tc = WHITE    if lbl == '1' else GRAY1
        r(ax, bx+i*0.026, y, 0.024, 0.020, fc=fc, ec=GRAY3)
        t(ax, bx+i*0.026+0.012, y+0.010, lbl, sz=6, color=tc, ha='center')

def info_box(ax, x, y, w, h, title, lines, fc=TEAL_B, bc=TEAL_T):
    r(ax, x, y, w, h, fc=fc, ec='#BEE5EB', lw=0.7)
    t(ax, x+0.010, y+h-0.015, title, sz=7, color=bc, bold=True)
    for i, line in enumerate(lines):
        t(ax, x+0.010, y+h-0.032-i*0.016, line, sz=5.8, color=bc)

def sum_box(ax, x, y, w, h, title, lines):
    r(ax, x, y, w, h, fc=WHITE, ec=GRAY3, lw=0.7)
    t(ax, x+0.010, y+h-0.015, title, sz=7, color=GRAY1, bold=True)
    for i, line in enumerate(lines):
        t(ax, x+0.010, y+h-0.032-i*0.016, line, sz=5.8,
          color=GRAY1, bold=(i == len(lines)-1))


# ═══════════════════════════════════════════════════════
#  WIREFRAME 10 — GESTIÓN DE JORNADAS
# ═══════════════════════════════════════════════════════
def make_jornadas():
    fig, ax = new_fig()
    navbar(ax)
    sidebar(ax, active_section='personal')

    # breadcrumb
    t(ax, CX, CT-0.008, 'Inicio  ›  Personal  ›  Gestión de jornadas', sz=6, color=GRAY2)
    # título
    t(ax, CX, CT-0.030, 'Gestión de Jornadas', sz=12, color=GRAY1, bold=True)

    # botones
    btn(ax, CX+CW-0.340, CT-0.045, 0.155, 0.026, '+ Nueva Jornada', BLUE_BTN)
    btn(ax, CX+CW-0.178, CT-0.045, 0.165, 0.026, 'Aprobar todas', GREEN)

    # filtros
    fy = CT - 0.055
    r(ax, CX, fy-0.040, CW, 0.048, fc=WHITE, ec=GRAY3, lw=0.7)
    lbls = [('Proyecto', CX+0.008), ('Empleado', CX+0.210), ('Estado', CX+0.355),
            ('Desde', CX+0.468), ('Hasta', CX+0.568)]
    for lbl, lx in lbls:
        t(ax, lx, fy-0.005, lbl, sz=5.8, color=GRAY2)
    sel(ax, CX+0.008, fy-0.038, 0.185, 0.026, 'Todos los proyectos')
    sel(ax, CX+0.210, fy-0.038, 0.130, 0.026, 'Todos')
    sel(ax, CX+0.355, fy-0.038, 0.098, 0.026, 'Todos')
    inp(ax, CX+0.468, fy-0.038, 0.085, 0.026, '01/04/2025')
    inp(ax, CX+0.568, fy-0.038, 0.085, 0.026, '30/04/2025')
    btn(ax, CX+0.666, fy-0.038, 0.060, 0.026, 'Filtrar')

    # tabla
    cols = ['Empleado', 'Proyecto', 'Fecha', 'Días', 'Monto (Bs)', 'Estado', 'Acciones']
    cw   = [0.140, 0.175, 0.070, 0.040, 0.078, 0.082, 0.240]
    ty   = fy - 0.048
    th(ax, CX, ty, sum(cw), 0.026, cols, cw)

    rows = [
        ('Roberto Lima',  'PRY-001 · Banco Sur',   '15/04/25', '1.0', '150.00', 'aprobada',  ''),
        ('Carmen Flores', 'PRY-001 · Banco Sur',   '15/04/25', '0.5', '75.00',  'aprobada',  ''),
        ('Roberto Lima',  'PRY-002 · Hotel Plaza', '16/04/25', '1.0', '150.00', 'pendiente', ''),
        ('Ana Torres',    'PRY-003 · Oficina A',   '16/04/25', '1.0', '130.00', 'pendiente', ''),
        ('Carmen Flores', 'PRY-002 · Hotel Plaza', '17/04/25', '0.5', '75.00',  'rechazada', ''),
        ('Roberto Lima',  'PRY-001 · Banco Sur',   '17/04/25', '1.0', '150.00', 'aprobada',  ''),
        ('Luis Mamani',   'PRY-003 · Oficina A',   '18/04/25', '1.0', '130.00', 'pendiente', ''),
        ('Ana Torres',    'PRY-001 · Banco Sur',   '18/04/25', '0.5', '65.00',  'aprobada',  ''),
    ]
    bc_map = {'aprobada': GREEN, 'pendiente': ORANGE, 'rechazada': RED}
    rh = 0.048
    bottom = tr(ax, CX, ty, rh, rows, cw, badge_col=5, bc_map=bc_map)

    # botones acción por fila
    for ri, row in enumerate(rows):
        ry  = ty - ri*rh - rh
        abx = CX + sum(cw[:6]) + 0.006
        if row[5] == 'pendiente':
            btn(ax, abx,       ry+0.010, 0.055, 0.020, 'Aprobar',  GREEN,    sz=5.8)
            btn(ax, abx+0.060, ry+0.010, 0.060, 0.020, 'Rechazar', RED,      sz=5.8)
        else:
            btn(ax, abx,       ry+0.010, 0.080, 0.020, 'Ver detalle', GRAY_BTN, sz=5.8)

    pag(ax, CX, bottom - 0.030)

    by = bottom - 0.065
    sum_box(ax, CX, by, CW*0.40, 0.055,
            'Resumen del período seleccionado',
            ['Total: 24  |  Aprobadas: 16  |  Pendientes: 6  |  Rechazadas: 2',
             'Monto total aprobado: Bs 2,400.00'])
    info_box(ax, CX+CW*0.41, by, CW*0.59, 0.055,
             'Jornadas automáticas',
             ['Al completar una tarea con 1 participante y contrato vigente,',
              'el sistema crea la jornada en estado pendiente automáticamente.'])

    fig.tight_layout(pad=0)
    return fig


# ═══════════════════════════════════════════════════════
#  WIREFRAME 11 — REGISTRO DE COMPRAS (sidebar activo=inventario)
# ═══════════════════════════════════════════════════════
def sidebar_inv(ax):
    """Sidebar con Compras activo."""
    top = 1.0 - NB_H
    r(ax, 0, 0, SB_W, top, fc=AZ_DARK, ec=AZ_DARK, lw=0, z=5)
    sy = top - 0.018

    def sep_label(text, color):
        nonlocal sy
        ax.plot([0.005, SB_W-0.005], [sy, sy], color='#FFFFFF22', lw=0.5,
                transform=ax.transAxes, zorder=6)
        sy -= 0.005
        t(ax, 0.012, sy, text.upper(), sz=5.5, color=color, bold=True, z=6)
        sy -= 0.022

    def item(label, active=False, indent=False):
        nonlocal sy
        h = 0.030
        ix = 0.008 if not indent else 0.022
        if active:
            r(ax, ix, sy-h, SB_W-ix-0.004, h, fc='#D4B84A33', ec=DORADO, lw=0.8, z=6)
        t(ax, ix+0.012, sy-h/2, label, sz=6.5,
          color=DORADO if active else WHITE, bold=active, z=7)
        sy -= h + 0.003

    def item_ch(label, exp=False):
        nonlocal sy
        h = 0.030
        t(ax, 0.020, sy-h/2, label, sz=6.5, color=WHITE, z=7)
        t(ax, SB_W-0.018, sy-h/2, '▾' if exp else '›', sz=6, color='#AAAAAA', z=7)
        sy -= h + 0.003

    sep_label('📁  Proyectos', DORADO)
    item('Clientes')
    item_ch('Proyectos')
    item_ch('Pagos Proyectos')
    item('Garantias')

    sep_label('👥  Personal', AZUL_SEC)
    item_ch('Empleados')
    item('Pagos a Empleados')

    sep_label('📦  Inventario', VERDE_SEC)
    item_ch('Insumos', exp=False)
    item('Proveedores')
    item('Compras', active=True)


def make_compras():
    fig, ax = new_fig()
    navbar(ax)
    sidebar_inv(ax)

    t(ax, CX, CT-0.008, 'Inicio  ›  Inventario  ›  Compras', sz=6, color=GRAY2)
    t(ax, CX, CT-0.030, 'Registro de Compras', sz=12, color=GRAY1, bold=True)
    btn(ax, CX+CW-0.175, CT-0.045, 0.162, 0.026, '+ Nueva Compra', BLUE_BTN)

    # filtros
    fy = CT - 0.055
    r(ax, CX, fy-0.040, CW*0.62, 0.048, fc=WHITE, ec=GRAY3, lw=0.7)
    lbls2 = [('Proveedor', CX+0.008), ('Insumo', CX+0.178), ('Desde', CX+0.322), ('Hasta', CX+0.420)]
    for lbl, lx in lbls2:
        t(ax, lx, fy-0.005, lbl, sz=5.8, color=GRAY2)
    sel(ax, CX+0.008, fy-0.038, 0.155, 0.026, 'Todos los proveedores')
    inp(ax, CX+0.178, fy-0.038, 0.128, 0.026, 'Buscar insumo...')
    inp(ax, CX+0.322, fy-0.038, 0.082, 0.026, '01/04/2025')
    inp(ax, CX+0.420, fy-0.038, 0.082, 0.026, '30/04/2025')
    btn(ax, CX+0.516, fy-0.038, 0.058, 0.026, 'Filtrar', fc=GRAY1)

    # alerta stock
    r(ax, CX+CW*0.635, fy-0.040, CW*0.365, 0.048, fc=WARN_B, ec='#FFEEBA', lw=0.7)
    t(ax, CX+CW*0.645, fy-0.006, '⚠  Alertas de stock', sz=7, color=WARN_T, bold=True)
    t(ax, CX+CW*0.645, fy-0.022, '3 insumos con stock bajo', sz=6, color=WARN_T)
    t(ax, CX+CW*0.645, fy-0.034, '1 insumo agotado – requiere compra urgente', sz=5.8, color=RED)

    # tabla
    cols2 = ['Proveedor', 'Insumo', 'Cant.', 'Unid.', 'P.Unit.(Bs)', 'Total(Bs)', 'Fecha', 'Factura', 'Acc.']
    cw2   = [0.125, 0.163, 0.038, 0.042, 0.082, 0.070, 0.052, 0.076, 0.177]
    ty2   = fy - 0.048
    th(ax, CX, ty2, sum(cw2), 0.026, cols2, cw2)

    rows2 = [
        ('TecnoSegur S.A.', 'Cámara IP 4MP Dahua',   '10','Unid.','850.00',  '8,500.00','02/04','F-001-0234',''),
        ('CablesCorp',      'Cable UTP Cat6',          '5', 'Rollo','320.00',  '1,600.00','03/04','F-002-0891',''),
        ('TecnoSegur S.A.', 'DVR 16ch Dahua',          '2', 'Unid.','1,200.00','2,400.00','05/04','F-001-0235',''),
        ('AlarmasPro',      'Sensor movimiento PIR',   '20','Unid.','85.00',   '1,700.00','08/04','F-003-0112',''),
        ('CablesCorp',      'Cable coaxial RG59',      '8', 'Rollo','180.00',  '1,440.00','10/04','F-002-0895',''),
        ('TecnoSegur S.A.', 'Fuente 12V 5A',           '15','Unid.','95.00',   '1,425.00','12/04','F-001-0240',''),
        ('AlarmasPro',      'Sirena exterior 20W',     '8', 'Unid.','145.00',  '1,160.00','15/04','F-003-0118',''),
        ('CablesCorp',      'Conector BNC caja x50',   '4', 'Caja', '55.00',   '220.00',  '18/04','F-002-0902',''),
    ]
    rh2 = 0.048
    bottom2 = tr(ax, CX, ty2, rh2, rows2, cw2)

    acc_start = CX + sum(cw2[:8])
    btn_w, btn_h = 0.038, 0.026
    for ri in range(len(rows2)):
        ry = ty2 - ri*rh2 - rh2
        # botón ⋮ centrado en la columna Acc.
        bx = acc_start + (cw2[8] - btn_w) / 2
        by = ry + (rh2 - btn_h) / 2
        r(ax, bx, by, btn_w, btn_h, fc=GRAY4, ec=GRAY3, lw=0.8, z=4)
        t(ax, bx + btn_w/2, by + btn_h/2, '⋮', sz=11, color=GRAY1, ha='center', z=5)

    pag(ax, CX, bottom2 - 0.030)

    by2 = bottom2 - 0.065
    sum_box(ax, CX, by2, CW*0.37, 0.055,
            'Resumen del período seleccionado',
            ['Total compras: 38  |  Insumos distintos: 12',
             'Inversión total: Bs 18,445.00'])
    info_box(ax, CX+CW*0.38, by2, CW*0.62, 0.055,
             'Costeo FIFO automático',
             ['Los lotes se consumen cronológicamente al asignar insumos a proyectos.',
              'El stock se actualiza automáticamente mediante señales Django.'])

    fig.tight_layout(pad=0)
    return fig


# ── Guardar ──────────────────────────────────────────────
make_jornadas().savefig(
    os.path.join(OUT, 'wf_10_jornadas.png'),
    dpi=150, bbox_inches='tight', facecolor=CONTENT_BG)
plt.close('all')
print("OK  wf_10_jornadas.png")

make_compras().savefig(
    os.path.join(OUT, 'wf_11_compras.png'),
    dpi=150, bbox_inches='tight', facecolor=CONTENT_BG)
plt.close('all')
print("OK  wf_11_compras.png")
