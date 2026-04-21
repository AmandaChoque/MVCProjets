"""Wireframe 07 — Lista de Empleados (employees.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='empleados')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

t(ax, MX+0.15, y0-0.38, 'Gestión de Empleados', size=12, bold=True, color=AZUL)
btn(ax, W-2.1, y0-0.56, 1.85, 0.38, '+ Nuevo Empleado', fc=AZUL, size=8)
draw_mostrar_contador(ax, MX, y0-0.8, MW)

filters = [
    ('Buscar por nombre o apellido', 4.0, 'text'),
    ('Cargo',                        2.2, 'select'),
]
y_card = draw_filter_card(ax, MX, y0-1.15, filters, MW)

col_defs = [('Empleado',0.12),('Cargo',2.8),('Carnet',4.4),
            ('Celular',5.9),('Proyecto Actual',7.2),('Fecha Reg.',9.3),('Acc.',10.8)]
y_th = draw_table_header(ax, MX, y_card, col_defs, MW)

cargo_colors = {
    'Administrador': '#dc3545',
    'Gerente':       '#0d6efd',
    'Instalador':    '#0dcaf0',
    'Técnico':       '#ffc107',
    'Secretaria':    '#198754',
}
cargo_tc = {
    'Administrador':'white','Gerente':'white',
    'Instalador':'#111','Técnico':'#111','Secretaria':'white'
}
filas = [
    ('Carlos Mamani Quispe','Instalador',  '7654321','76543210','Seg. Edificio C.','10/01/2025'),
    ('Ana Flores Vargas',   'Técnico',     '8765432','71234567','CCTV Almacén',    '15/02/2025'),
    ('Luis Quispe Apaza',   'Instalador',  '9876543','78901234','—',               '01/03/2025'),
    ('María García López',  'Secretaria',  '1234567','72345678','—',               '20/01/2024'),
    ('Pedro Rojas Condori', 'Gerente',     '2345678','79012345','—',               '05/06/2023'),
]
CX = [MX+0.12, MX+2.8, MX+4.4, MX+5.9, MX+7.2, MX+9.3, MX+10.8]
for i, (nom, cargo, ci, cel, proy, fecha) in enumerate(filas):
    yr = y_th - 0.2 - i*0.44
    fc_r = 'white' if i%2==0 else '#f8f9fa'
    rect(ax, MX, yr-0.2, MW, 0.42, fc=fc_r, ec='#dee2e6', lw=0.4)
    t(ax, CX[0], yr, nom,   size=7.5, bold=True, color='#222')
    badge(ax, CX[1]-0.05, yr-0.14, 1.2, 0.28, cargo,
          fc=cargo_colors[cargo], tc=cargo_tc[cargo], size=6.2)
    t(ax, CX[2], yr, ci,    size=7.5, color='#555')
    t(ax, CX[3], yr, cel,   size=7.5, color='#555')
    if proy != '—':
        badge(ax, CX[4]-0.05, yr-0.14, 1.9, 0.28, proy, fc='#0d6efd', size=6)
    else:
        t(ax, CX[4], yr, '—', size=7.5, color='#aaa')
    t(ax, CX[5], yr, fecha, size=7.5, color='#888')
    rounded(ax, CX[6]-0.02, yr-0.14, 0.42, 0.28, fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(ax, CX[6]+0.19, yr, '⋮', size=10, ha='center', color='#555')

rect(ax, MX, y_th-2.6, MW, 2.6, fc='none', ec='#dee2e6', lw=1.0)
draw_pagination(ax, cx=W/2, y=0.5)
draw_caption(ax, 'Figura XX: Lista de Empleados — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_07_empleados.png')
