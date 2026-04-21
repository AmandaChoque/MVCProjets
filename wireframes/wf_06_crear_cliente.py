"""Wireframe 06 — Crear Cliente (crear_cliente.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='clientes')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Breadcrumb ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.35, 'Contratantes  >  Nuevo registro',
  size=8, color='#6c757d')

# ── Card ──────────────────────────────────────────────────────────────────────
rect(ax, MX+0.1, 0.55, MW-0.2, y0-1.0, fc='white', ec='#dee2e6', lw=0.8)

LX = MX + 0.45
RX = MX + 5.9
FW = 4.7

def fld(ax, x, y, label, req=False, select=False, ph=''):
    star = ' *' if req else ''
    t(ax, x, y+0.08, label+star, size=7.8, bold=True, color='#374151')
    input_field(ax, x, y-0.3, FW, 0.32, placeholder=ph, select=select)

# ── Columna izquierda ─────────────────────────────────────────────────────────
fld(ax, LX, y0-1.2,  'Rol de Contacto',      select=True)
fld(ax, LX, y0-2.05, 'NIT / CI')
fld(ax, LX, y0-2.9,  'Tipo de contratante',  req=True, select=True)
fld(ax, LX, y0-3.75, 'Celular / Teléfono',   req=True)

# ── Columna derecha ───────────────────────────────────────────────────────────
fld(ax, RX, y0-1.2,  'Nombres',              req=True)
fld(ax, RX, y0-2.05, 'Apellido paterno',     req=True)
fld(ax, RX, y0-2.9,  'Apellido materno')
fld(ax, RX, y0-3.75, 'Correo electrónico')

# ── Dirección (ancho completo) ────────────────────────────────────────────────
t(ax, LX, y0-4.6, 'Dirección *', size=7.8, bold=True, color='#374151')
input_field(ax, LX, y0-4.98, MW-0.75, 0.32, placeholder='Dirección completa...')

t(ax, LX, y0-5.42, '* Campos obligatorios', size=7.5, color='#888', italic=True)

# ── Botones ───────────────────────────────────────────────────────────────────
btn(ax, LX, 0.75, 1.5, 0.38, 'Cancelar', fc='white', tc='#555', ec='#bbb')
btn(ax, MW+MX-1.55, 0.75, 1.4, 0.38, 'Guardar', fc=AZUL)

draw_caption(ax, 'Figura XX: Registro de Cliente — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_06_crear_cliente.png')
