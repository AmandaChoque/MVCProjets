"""Wireframe 05 — Lista de Clientes (clientes.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='clientes')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Encabezado ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.38, 'Gestión de Clientes / Contratantes',
  size=12, bold=True, color=AZUL)
btn(ax, W-2.0, y0-0.56, 1.75, 0.38, '+ Nuevo Cliente', fc=AZUL, size=8)

draw_mostrar_contador(ax, MX, y0-0.8, MW)

# ── Filtros ───────────────────────────────────────────────────────────────────
filters = [
    ('Nombres o Apellido', 3.0, 'text'),
    ('NIT / CI',           2.2, 'text'),
    ('Tipo',               2.0, 'select'),
]
y_card = draw_filter_card(ax, MX, y0-1.15, filters, MW)

# ── Tabla ─────────────────────────────────────────────────────────────────────
col_defs = [('Cliente',0.12),('NIT/CI',2.5),('Cargo',4.4),
            ('Tipo',5.8),('Contacto',7.3),('Acciones',9.8)]
y_th = draw_table_header(ax, MX, y_card, col_defs, MW)

filas = [
    ('Juan Pérez García',    '12345678', 'Propietario',   'Empresa',        '76543210'),
    ('María López Castro',   '87654321', 'Representante', 'Personal',       '71234567'),
    ('Carlos Mamani Quispe', '11223344', 'Director',      'Entidad Pública','78901234'),
    ('Ana Flores Vargas',    '44332211', 'Propietario',   'Empresa',        '72345678'),
    ('Luis Quispe Apaza',    '55667788', 'Representante', 'Personal',       '79012345'),
]
tipo_colors = {'Empresa':'#0d6efd','Personal':'#198754','Entidad Pública':'#ffc107'}
tipo_tc     = {'Empresa':'white',  'Personal':'white',  'Entidad Pública':'#111'}

CX = [MX+0.12, MX+2.5, MX+4.4, MX+5.8, MX+7.3, MX+9.8]
for i, (nom, nit, cargo, tipo, tel) in enumerate(filas):
    yr = y_th - 0.2 - i*0.44
    fc_r = 'white' if i%2==0 else '#f8f9fa'
    rect(ax, MX, yr-0.2, MW, 0.42, fc=fc_r, ec='#dee2e6', lw=0.4)
    t(ax, CX[0], yr, nom,   size=7.5, bold=True, color='#222')
    t(ax, CX[1], yr, nit,   size=7.5, color='#555')
    t(ax, CX[2], yr, cargo, size=7.5, color='#555')
    badge(ax, CX[3]-0.05, yr-0.14, 1.2, 0.28, tipo,
          fc=tipo_colors[tipo], tc=tipo_tc[tipo], size=6.5)
    t(ax, CX[4], yr, tel,   size=7.5, color='#555')
    rounded(ax, CX[5]-0.02, yr-0.14, 0.42, 0.28,
            fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(ax, CX[5]+0.19, yr, '⋮', size=10, ha='center', color='#555')

rect(ax, MX, y_th-2.6, MW, 2.6, fc='none', ec='#dee2e6', lw=1.0)
draw_pagination(ax, cx=W/2, y=0.5)
draw_caption(ax, 'Figura XX: Lista de Clientes — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_05_clientes.png')
