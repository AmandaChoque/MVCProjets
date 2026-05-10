"""Wireframe — Listado de Proyectos (projects.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='proyectos')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Encabezado ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.38, 'Gestión de Proyectos', size=12, bold=True, color=AZUL)
btn(ax, W-2.05, y0-0.55, 1.80, 0.38, '+ Nuevo Proyecto', fc=AZUL)

# ── Mostrar / contador ────────────────────────────────────────────────────────
draw_mostrar_contador(ax, MX, y0-0.88, MW)

# ── Card de filtros ───────────────────────────────────────────────────────────
FCARD_Y = y0 - 1.25
FCARD_H = 1.40
rect(ax, MX, FCARD_Y - FCARD_H, MW, FCARD_H, fc='white', ec='#ddd', lw=0.8)

# Fila 1: texto + selects + botones
labels_f1 = ['Nombre del proyecto', 'Estado', 'Tipo', 'Estado de pago']
widths_f1  = [2.80,                   1.65,    1.65,    1.65]
fx = MX + 0.18
for lbl, fw in zip(labels_f1, widths_f1):
    t(ax, fx, FCARD_Y - 0.20, lbl, size=7, color='#777')
    if lbl == 'Nombre del proyecto':
        input_field(ax, fx, FCARD_Y - 0.50, fw, 0.26, placeholder='Buscar por nombre...')
    else:
        input_field(ax, fx, FCARD_Y - 0.50, fw, 0.26, select=True)
    fx += fw + 0.14
btn(ax, fx,       FCARD_Y - 0.50, 0.90, 0.26, 'Filtrar', fc='#212529', size=7.5)
btn(ax, fx + 1.0, FCARD_Y - 0.50, 0.82, 0.26, 'Limpiar', fc='white', tc='#555', size=7.5, ec='#bbb')

# Fila 2: fechas
labels_f2 = ['Inicio desde', 'Inicio hasta', 'Fin desde', 'Fin hasta']
fx2 = MX + 0.18
for lbl in labels_f2:
    t(ax, fx2, FCARD_Y - 0.86, lbl, size=7, color='#777')
    input_field(ax, fx2, FCARD_Y - 1.16, 2.20, 0.26, placeholder='dd/mm/aaaa')
    fx2 += 2.20 + 0.17

TABLE_Y = FCARD_Y - FCARD_H

# ── Cabecera de tabla ─────────────────────────────────────────────────────────
col_defs = [
    ('Código',              0.10),
    ('Nombre del Proyecto', 0.90),
    ('Contratante',         3.25),
    ('Tipo',                5.20),
    ('Estado',              6.45),
    ('Estado Pago',         7.65),
    ('Monto (Bs.)',         8.95),
    ('Acc.',               10.30),
]
HDR_BOT = draw_table_header(ax, MX, TABLE_Y, col_defs, MW)
col_x = [MX + cx for _, cx in col_defs]

# ── Filas de datos ────────────────────────────────────────────────────────────
filas = [
    ('PR-001', 'Seg. Edificio Central', 'Juan Pérez',    'Instalación',  'En Progreso', 'Parcial',   '18,500.00'),
    ('PR-002', 'CCTV Almacén Norte',    'Ana Flores',    'Mantenimiento','Completado',  'Pagado',    ' 9,200.00'),
    ('PR-003', 'Alarmas Oficina Sur',   'Carlos Mamani', 'Instalación',  'Pendiente',   'No Pagado', '12,000.00'),
    ('PR-004', 'DVR Sucursal Este',     'Luis Quispe',   'Instalación',  'En Progreso', 'Parcial',   ' 7,800.00'),
    ('PR-005', 'Cámaras IP Centro',     'María García',  'Instalación',  'Completado',  'Pagado',    '15,400.00'),
]
estado_colors = {'En Progreso': '#0d6efd', 'Completado': '#198754', 'Pendiente': '#ffc107'}
pago_colors   = {'Pagado': '#198754', 'Parcial': '#0dcaf0', 'No Pagado': '#dc3545'}
pago_tc       = {'Pagado': 'white',   'Parcial': '#111',    'No Pagado': 'white'}

for i, (cod, nom, cont, tipo, est, pago, monto) in enumerate(filas):
    yr     = HDR_BOT - 0.22 - i * 0.44
    fc_row = 'white' if i % 2 == 0 else '#f8f9fa'
    rect(ax, MX, yr - 0.20, MW, 0.42, fc=fc_row, ec='#dee2e6', lw=0.4)
    t(ax, col_x[0], yr, cod,  size=7.0, color='#888')
    t(ax, col_x[1], yr, nom,  size=7.5, bold=True, color='#222')
    t(ax, col_x[2], yr, cont, size=7.5, color='#444')
    badge(ax, col_x[3]-0.05, yr-0.13, 1.05, 0.26, tipo[:10],
          fc='#6c757d', size=6.5)
    badge(ax, col_x[4]-0.05, yr-0.13, 1.10, 0.26, est,
          fc=estado_colors[est], tc='white' if est != 'Pendiente' else '#111', size=6.5)
    badge(ax, col_x[5]-0.05, yr-0.13, 1.10, 0.26, pago,
          fc=pago_colors[pago], tc=pago_tc[pago], size=6.5)
    t(ax, col_x[6], yr, monto, size=7.5, bold=True, color='#333')
    rounded(ax, col_x[7]-0.02, yr-0.14, 0.40, 0.28,
            fc='#f8f9fa', ec='#ccc', lw=0.7, pad=0.03)
    t(ax, col_x[7]+0.18, yr, '⋮', size=10, ha='center', color='#555')

# Borde exterior tabla
TABLE_BOT = HDR_BOT - len(filas) * 0.44 - 0.02
rect(ax, MX, TABLE_BOT, MW, TABLE_Y - TABLE_BOT, fc='none', ec='#dee2e6', lw=1.0)

# ── Paginación ────────────────────────────────────────────────────────────────
draw_pagination(ax, cx=W/2, y=TABLE_BOT - 0.28, W=W)

draw_caption(ax, 'Figura XX: Listado de Proyectos — Sistema SOBOTEC S.R.L.', W=W, H=H)
save(fig, 'wf_lista_proyectos.png')
