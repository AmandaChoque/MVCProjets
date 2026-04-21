"""Wireframe 09 — Lista de Pagos (payments.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='pagos')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

t(ax, MX+0.15, y0-0.38, 'Gestión de Pagos', size=12, bold=True, color=AZUL)
btn(ax, W-1.95, y0-0.56, 1.75, 0.38, '+ Nuevo Pago', fc=AZUL, size=8)
draw_mostrar_contador(ax, MX, y0-0.8, MW)

filters = [
    ('Nombre del proyecto', 4.5, 'text'),
    ('Método de Pago',      2.5, 'select'),
]
y_card = draw_filter_card(ax, MX, y0-1.15, filters, MW)

col_defs = [('Proyecto',0.12),('Monto (Bs.)',4.5),
            ('Fecha',6.2),('Método',7.8),('Acciones',10.0)]
y_th = draw_table_header(ax, MX, y_card, col_defs, MW)

filas = [
    ('Seg. Edificio Central', '9,250.00',  '01/03/2026', 'Transferencia'),
    ('CCTV Almacén Norte',    '9,200.00',  '15/01/2026', 'Efectivo'),
    ('Alarmas Oficina Sur',   '6,000.00',  '10/02/2026', 'Transferencia'),
    ('DVR Sucursal Este',     '3,900.00',  '20/03/2026', 'Efectivo'),
    ('Cámaras IP Centro',     '15,400.00', '05/04/2026', 'Transferencia'),
]
metodo_fc = {'Transferencia':'#0d6efd','Efectivo':'#0dcaf0'}
metodo_tc = {'Transferencia':'white',  'Efectivo':'#111'}

CX = [MX+0.12, MX+4.5, MX+6.2, MX+7.8, MX+10.0]
for i, (proy, monto, fecha, metodo) in enumerate(filas):
    yr = y_th - 0.2 - i*0.44
    fc_r = 'white' if i%2==0 else '#f8f9fa'
    rect(ax, MX, yr-0.2, MW, 0.42, fc=fc_r, ec='#dee2e6', lw=0.4)
    t(ax, CX[0], yr, proy,  size=7.5, bold=True, color='#222')
    t(ax, CX[1], yr, monto, size=7.5, bold=True, color='#198754')
    t(ax, CX[2], yr, fecha, size=7.5, color='#555')
    badge(ax, CX[3]-0.05, yr-0.14, 1.3, 0.28, metodo,
          fc=metodo_fc[metodo], tc=metodo_tc[metodo], size=6.5)
    rounded(ax, CX[4]-0.02, yr-0.14, 0.42, 0.28, fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(ax, CX[4]+0.19, yr, '⋮', size=10, ha='center', color='#555')

rect(ax, MX, y_th-2.6, MW, 2.6, fc='none', ec='#dee2e6', lw=1.0)

# Resumen total al pie de tabla
rect(ax, MX, y_th-3.0, MW, 0.32, fc='#f0f4fa', ec='#dee2e6', lw=0.6)
t(ax, MX+0.2, y_th-2.84, 'Total mostrado:', size=8, bold=True, color='#333')
t(ax, MX+1.9, y_th-2.84, 'Bs. 43,750.00', size=8, bold=True, color='#198754')

draw_pagination(ax, cx=W/2, y=0.5)
draw_caption(ax, 'Figura XX: Lista de Pagos — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_09_pagos.png')
