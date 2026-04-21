"""Wireframe 03 — Editar Proyecto (project_detail.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='proyectos')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Breadcrumb ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.35, 'Proyectos  >  Editar — Proyecto Edificio Central',
  size=8, color='#6c757d')

# ── Card principal ────────────────────────────────────────────────────────────
rect(ax, MX+0.1, 0.6, MW-0.2, y0-1.1, fc='white', ec='#dee2e6', lw=0.8)

# ── Columna izquierda ─────────────────────────────────────────────────────────
LX = MX + 0.45
RX = MX + 5.9
FW = 4.6

def field(y, label, val='', req=False):
    star = ' *' if req else ''
    t(ax, LX, y+0.06, label + star, size=7.5, bold=True, color='#374151')
    input_field(ax, LX, y-0.28, FW, 0.3, placeholder=val)

field(y0-1.25, 'Código del proyecto',       'PR-001',         req=True)
field(y0-2.0,  'Nombre del proyecto',        'Seg. Edificio Central', req=True)
# Textarea descripción
t(ax, LX, y0-2.74, 'Descripción', size=7.5, bold=True, color='#374151')
rect(ax, LX, y0-3.5, FW, 0.65, fc='white', ec='#bbb', lw=0.7)
t(ax, LX+0.1, y0-3.17, 'Descripción del proyecto...', size=7, color='#bbb')
# Observación
t(ax, LX, y0-3.75, 'Observación', size=7.5, bold=True, color='#374151')
rect(ax, LX, y0-4.42, FW, 0.55, fc='white', ec='#bbb', lw=0.7)
# Monto
field(y0-4.7, 'Monto total (Bs.)', '18500.00', req=True)

# ── Columna derecha ───────────────────────────────────────────────────────────
def rfield(y, label, val='', req=False, readonly=False):
    star = ' *' if req else ''
    t(ax, RX, y+0.06, label + star, size=7.5, bold=True, color='#374151')
    fc = '#f8f9fa' if readonly else 'white'
    ec = '#dee2e6' if readonly else '#bbb'
    rounded(ax, RX, y-0.28, FW, 0.3, fc=fc, ec=ec, lw=0.7, pad=0.03)
    color = '#9ca3af' if readonly else '#555'
    if val:
        t(ax, RX+0.1, y-0.13, val, size=7.5, color=color)
    if not readonly:
        t(ax, RX+FW-0.2, y-0.13, '▾', size=8, ha='center', color='#888')

rfield(y0-1.25, 'Estado del proyecto',           'En Progreso ▾',     req=True)
rfield(y0-2.0,  'Tipo de proyecto',              'Instalación Nueva ▾',req=True)
rfield(y0-2.75, 'Cliente / Contratante',         'Juan Pérez García ▾',req=True)
rfield(y0-3.5,  'Fecha de Inicio de Ejecución',  '01/03/2026',         readonly=True)
rfield(y0-4.25, 'Fecha de Culminación',          '— (automático)',      readonly=True)

# Nota campos obligatorios
t(ax, MX+0.45, y0-5.2, '* Campos obligatorios', size=7.5, color='#888', italic=True)

# ── Botones ───────────────────────────────────────────────────────────────────
btn(ax, MX+0.45, 0.82, 1.5, 0.38, 'Cancelar',
    fc='white', tc='#555', ec='#bbb')
btn(ax, MW-4.8+MX, 0.82, 2.5, 0.38, 'Marcar completado',
    fc='white', tc='#198754', ec='#198754')
btn(ax, MW-2.1+MX, 0.82, 1.2, 0.38, 'Eliminar',
    fc='white', tc='#dc3545', ec='#dc3545')
btn(ax, MW-0.75+MX, 0.82, 1.4, 0.38, 'Actualizar', fc=AZUL)

draw_caption(ax, 'Figura XX: Editar Proyecto — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_03_editar_proyecto.png')
