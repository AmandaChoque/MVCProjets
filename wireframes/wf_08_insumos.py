"""Wireframe 08 — Catálogo de Insumos (insumos.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='insumos')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

t(ax, MX+0.15, y0-0.38, 'Catálogo de Insumos', size=12, bold=True, color=AZUL)
btn(ax, W-2.0, y0-0.56, 1.75, 0.38, '+ Nuevo Insumo', fc=AZUL, size=8)
draw_mostrar_contador(ax, MX, y0-0.8, MW)

filters = [
    ('Nombre o marca',      3.2, 'text'),
    ('Todas las categorías',2.5, 'select'),
    ('Todos los stocks',    2.0, 'select'),
]
y_card = draw_filter_card(ax, MX, y0-1.15, filters, MW)

col_defs = [('Nombre',0.12),('Marca',2.5),('Modelo',4.2),
            ('Categoría',5.6),('Stock',7.8),('Acciones',10.0)]
y_th = draw_table_header(ax, MX, y_card, col_defs, MW)

cat_colors = {
    'Cámara IP':    '#0d6efd',
    'DVR/NVR':      '#212529',
    'Sensor':       '#ffc107',
    'Cable':        '#0dcaf0',
    'Alarma':       '#dc3545',
    'Fuente':       '#198754',
}
stock_data = [
    ('Cámara IP Hikvision 4MP', 'Hikvision','DS-2CD2143', 'Cámara IP', 25, 'ok'),
    ('DVR 8 canales',           'Dahua',    'DHI-XVR5108','DVR/NVR',   8,  'ok'),
    ('Sensor de movimiento',    'Paradox',  'PMD-Q75',    'Sensor',    3,  'bajo'),
    ('Cable coaxial 305m',      'Genérico', '—',          'Cable',     0,  'agotado'),
    ('Fuente regulada 12V 5A',  'Syscom',   'SY-12V5A',   'Fuente',    15, 'ok'),
]
stock_fc = {'ok':'#198754','bajo':'#ffc107','agotado':'#dc3545'}
stock_tc = {'ok':'white',  'bajo':'#111',   'agotado':'white'}
stock_lbl= {'ok':'{} und','bajo':'Stock bajo ({} und)','agotado':'Sin stock ({} und)'}

CX = [MX+0.12, MX+2.5, MX+4.2, MX+5.6, MX+7.8, MX+10.0]
for i, (nom, marca, modelo, cat, stk, status) in enumerate(stock_data):
    yr = y_th - 0.2 - i*0.44
    fc_r = 'white' if i%2==0 else '#f8f9fa'
    rect(ax, MX, yr-0.2, MW, 0.42, fc=fc_r, ec='#dee2e6', lw=0.4)
    t(ax, CX[0], yr, nom,    size=7.5, bold=True, color='#222')
    t(ax, CX[1], yr, marca,  size=7.5, color='#888')
    t(ax, CX[2], yr, modelo, size=7.5, color='#888')
    badge(ax, CX[3]-0.05, yr-0.14, 1.1, 0.28, cat,
          fc=cat_colors.get(cat,'#6c757d'), size=6.2)
    label = stock_lbl[status].format(stk)
    badge(ax, CX[4]-0.05, yr-0.14, 2.0, 0.28, label,
          fc=stock_fc[status], tc=stock_tc[status], size=6.2)
    rounded(ax, CX[5]-0.02, yr-0.14, 0.42, 0.28, fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(ax, CX[5]+0.19, yr, '⋮', size=10, ha='center', color='#555')

rect(ax, MX, y_th-2.6, MW, 2.6, fc='none', ec='#dee2e6', lw=1.0)
draw_pagination(ax, cx=W/2, y=0.5)
draw_caption(ax, 'Figura XX: Catálogo de Insumos — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_08_insumos.png')
