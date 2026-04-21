"""Helpers compartidos para todos los wireframes SOBOTEC."""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

# ── Paleta SOBOTEC ────────────────────────────────────────────────────────────
AZUL_DARK  = '#0F2D5A'
AZUL       = '#1B4D90'
DORADO     = '#D4B84A'
DORADO_LUZ = '#F0D878'
BG         = '#f1f3f6'
VERDE_SEC  = '#7bd9a5'
AZUL_SEC   = '#93c5fd'

def new_fig(w=14, h=10):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    fig.patch.set_facecolor('white')
    return fig, ax

def rect(ax, x, y, w, h, fc='white', ec='#ccc', lw=1.0, z=2):
    ax.add_patch(patches.Rectangle((x, y), w, h,
                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))

def rounded(ax, x, y, w, h, fc='white', ec='#ccc', lw=1.0, pad=0.05, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad={pad}",
                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z))

def t(ax, x, y, s, size=8, bold=False, ha='left', va='center',
      color='black', italic=False, z=4):
    ax.text(x, y, s, fontsize=size,
            fontweight='bold' if bold else 'normal',
            fontstyle='italic' if italic else 'normal',
            ha=ha, va=va, color=color, zorder=z)

def hline(ax, x0, x1, y, color='#ddd', lw=0.5):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, zorder=3)

def badge(ax, x, y, w, h, label, fc, tc='white', size=6.8):
    rounded(ax, x, y, w, h, fc=fc, ec='none', lw=0, pad=0.03, z=4)
    t(ax, x + w/2, y + h/2, label, size=size, bold=True, ha='center', color=tc, z=5)

def btn(ax, x, y, w, h, label, fc, tc='white', size=7.5, ec='none', lw=0.8):
    rounded(ax, x, y, w, h, fc=fc, ec=ec, lw=lw, pad=0.04, z=3)
    t(ax, x + w/2, y + h/2, label, size=size, bold=True, ha='center', color=tc, z=4)

def input_field(ax, x, y, w, h, placeholder='', select=False, value=''):
    rounded(ax, x, y, w, h, fc='white', ec='#bbb', lw=0.7, pad=0.03)
    if select:
        t(ax, x + 0.1, y + h/2, value or 'Todos', size=7, color='#555')
        t(ax, x + w - 0.18, y + h/2, '▾', size=7, ha='center', color='#888')
    elif placeholder:
        t(ax, x + 0.1, y + h/2, placeholder, size=6.8, color='#bbb')

def navbar(ax, W=14):
    rect(ax, 0, W/14*9.35, W, W/14*0.65, fc=AZUL, ec=AZUL_DARK, lw=0)

def draw_navbar(ax, W=14, H=10, nb_h=0.65):
    """Dibuja navbar y retorna y_base (donde empieza sidebar/content)."""
    y0 = H - nb_h
    rect(ax, 0, y0, W, nb_h, fc=AZUL, ec=AZUL_DARK, lw=0)
    rounded(ax, 0.15, y0 + 0.12, 0.42, 0.42, fc='#ffffff22', ec='#ffffff44', lw=0.5, pad=0.02)
    t(ax, 0.36, y0 + nb_h/2, '▣', size=10, ha='center', color='white')
    t(ax, 0.68, y0 + nb_h/2, 'SOBOTEC S.R.L.', size=12, bold=True, color=DORADO)
    rounded(ax, W-2.0, y0+0.16, 0.46, 0.34, fc='none', ec='#ffffff66', lw=0.7, pad=0.02)
    t(ax, W-1.77, y0 + nb_h/2, '🔔', size=9, ha='center', color='white')
    rounded(ax, W-1.42, y0+0.16, 1.28, 0.34, fc='none', ec='#ffffff66', lw=0.7, pad=0.02)
    t(ax, W-0.78, y0 + nb_h/2, 'usuario ▾', size=8, ha='center', color='white')
    return y0  # top of sidebar/content

def draw_sidebar(ax, H=10, nb_h=0.65, active='proyectos'):
    """Dibuja sidebar y retorna MX (x donde empieza el contenido)."""
    SH = H - nb_h
    rect(ax, 0, 0, 2.75, SH, fc=AZUL, ec=AZUL_DARK, lw=0)

    def ss(y, label, color):
        hline(ax, 0.1, 2.65, y + 0.04, color='#ffffff22', lw=0.6)
        t(ax, 0.18, y - 0.1, label.upper(), size=6, bold=True, color=color)

    def si(y, icon, label, is_active=False, indent=False):
        ix = 0.35 if not indent else 0.55
        if is_active:
            rect(ax, 0.05, y-0.18, 2.65, 0.36, fc='#D4B84A33', ec='none', lw=0)
            ax.plot([0.05, 0.05], [y-0.18, y+0.18],
                    color=DORADO, linewidth=2.5, zorder=5)
            color = DORADO_LUZ
        else:
            color = '#ffffffcc'
        t(ax, ix, y, f'{icon}  {label}',
          size=7.5 if not indent else 7.0, color=color, bold=is_active)

    # Mi Trabajo — solo visible para roles de campo (instalador / técnico)
    mi_trabajo_active = active == 'mi_trabajo'
    if mi_trabajo_active:
        rect(ax, 0.05, SH-0.53, 2.65, 0.36, fc='#D4B84A33', ec='none', lw=0)
        ax.plot([0.05, 0.05], [SH-0.53, SH-0.17],
                color=DORADO, linewidth=2.5, zorder=5)
        color_mt = DORADO_LUZ
    else:
        color_mt = '#ffffffcc'
    t(ax, 0.35, SH-0.35, f'📱  Mi Trabajo',
      size=7.5, color=color_mt, bold=mi_trabajo_active)
    # Badge "[campo]" aclarando el rol
    rounded(ax, 1.85, SH-0.48, 0.75, 0.22,
            fc='#ffffff18', ec='#ffffff44', lw=0.5, pad=0.02, z=4)
    t(ax, 2.22, SH-0.37, 'campo', size=5.5, ha='center', color='#ffffff88')

    ss(SH - 0.68, '⬛ Proyectos', DORADO)
    si(SH-1.03,  '👤', 'Clientes',            active == 'clientes')
    si(SH-1.41,  '📁', 'Proyectos  ▾',        active == 'proyectos')
    si(SH-1.78,  '▸',  'Listar',              active == 'proyectos', indent=True)
    si(SH-2.13,  '▸',  'Reporte',             False,                 indent=True)
    si(SH-2.48,  '▸',  'Análisis',            False,                 indent=True)
    si(SH-2.85,  '💰', 'Pagos Proyectos  ▾',  active == 'pagos')

    ss(SH-3.27, '👥 Personal', AZUL_SEC)
    si(SH-3.61,  '👥', 'Empleados  ▾',        active == 'empleados')
    si(SH-3.98,  '💳', 'Pagos a Empleados',   False)
    si(SH-4.33,  '📋', 'Plantillas de Tareas',False)

    ss(SH-4.73, '📦 Inventario', VERDE_SEC)
    si(SH-5.08,  '📦', 'Insumos  ▾',          active == 'insumos')
    si(SH-5.43,  '🛒', 'Compras',             False)
    si(SH-5.78,  '🚚', 'Proveedores',         False)

    return 2.9  # MX

def draw_pagination(ax, cx=7.0, y=0.5, W=14):
    pag = [('Anterior', 1.0), ('1', 0.38), ('2', 0.38), ('3', 0.38), ('Siguiente', 1.0)]
    px = cx - 1.6
    for lbl, w in pag:
        activo = lbl == '1'
        rounded(ax, px, y-0.16, w, 0.32,
                fc=AZUL if activo else 'white', ec='#dee2e6', lw=0.8, pad=0.03)
        t(ax, px + w/2, y, lbl, size=7.5, ha='center',
          color='white' if activo else '#555', bold=activo)
        px += w + 0.06

def draw_caption(ax, texto, W=14, y=0.22, H=10):
    t(ax, W/2, y, texto, size=9, ha='center', italic=True, color='#555')
    rect(ax, 0, 0, W, H, fc='none', ec='#999', lw=1.5)

def draw_mostrar_contador(ax, MX, y_top, MW=11.1):
    t(ax, MX+0.15, y_top, 'Mostrar:', size=8, color='#666')
    input_field(ax, MX+0.95, y_top-0.16, 0.75, 0.28, select=True, value='10')
    t(ax, MX+MW, y_top, 'Mostrando 1 – 10 de 12 registros',
      size=7.5, ha='right', color='#888')

def draw_filter_card(ax, MX, y_top, filters, MW=11.1):
    """filters = lista de (label, w, tipo) donde tipo='text'|'select'|'date'"""
    CARD_H = 0.75
    rect(ax, MX, y_top - CARD_H, MW, CARD_H, fc='white', ec='#ddd', lw=0.8)
    fx = MX + 0.18
    for label, fw, tipo in filters:
        t(ax, fx, y_top - 0.18, label, size=7, color='#777')
        if tipo == 'text':
            input_field(ax, fx, y_top - CARD_H + 0.18, fw, 0.26,
                        placeholder=label + '...')
        elif tipo == 'select':
            input_field(ax, fx, y_top - CARD_H + 0.18, fw, 0.26, select=True)
        elif tipo == 'date':
            input_field(ax, fx, y_top - CARD_H + 0.18, fw, 0.26,
                        placeholder='dd/mm/aaaa')
        fx += fw + 0.16
    # Botones al final
    btn(ax, fx, y_top - CARD_H + 0.18, 0.9, 0.26, 'Filtrar', fc='#212529', size=7.5)
    btn(ax, fx+1.0, y_top - CARD_H + 0.18, 0.85, 0.26, 'Limpiar',
        fc='white', tc='#555', size=7.5, ec='#bbb')
    return y_top - CARD_H  # y inferior de la card

def draw_table_header(ax, MX, y_top, col_defs, MW=11.1):
    """col_defs = [(label, x_offset), ...]"""
    rect(ax, MX, y_top - 0.38, MW, 0.38, fc='#e9ecef', ec='#dee2e6', lw=0.8)
    for label, cx in col_defs:
        t(ax, MX + cx, y_top - 0.19, label.upper(), size=6.5, bold=True, color='#555')
    return y_top - 0.38

def save(fig, fname):
    fig.tight_layout(pad=0)
    fig.savefig(f'wireframes/{fname}', dpi=160,
                bbox_inches='tight', facecolor='white')
    plt.show()
    print(f'Guardado: wireframes/{fname}')
