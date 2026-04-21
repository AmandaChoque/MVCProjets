"""Wireframe 02 — Dashboard / Panel de Control (home.html)"""
import sys, math
sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 13
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='dashboard')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Encabezado ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.38, 'Panel de Control', size=12, bold=True, color=AZUL)
t(ax, MX+0.15, y0-0.65, 'Resumen general del sistema — SOBOTEC S.R.L.',
  size=8, color='#6c757d', italic=True)

# Filtro año/mes (derecha)
t(ax, W-4.6, y0-0.45, '⚙ Período:', size=8, color='#6c757d')
input_field(ax, W-3.9, y0-0.60, 1.3, 0.28, select=True, value='2026')
input_field(ax, W-2.45, y0-0.60, 1.3, 0.28, select=True, value='Abril')

# ── Alertas accordion ─────────────────────────────────────────────────────────
# Fila de título con badge separado
t(ax, MX+0.15, y0-1.08, '🔔  Alertas del Sistema', size=9, bold=True, color='#333')
badge(ax, MX+3.35, y0-1.20, 0.38, 0.24, '3', fc='#dc3545', size=7)

# Accordion: Plazos Vencidos (expandido)
rect(ax, MX+0.1, y0-1.50, MW-0.2, 0.36, fc='#fff5f5', ec='#dee2e6', lw=0.8)
t(ax, MX+0.35, y0-1.32, '📅  Plazos Vencidos', size=8.5, bold=True, color='#dc3545')
badge(ax, MX+4.5, y0-1.42, 0.38, 0.22, '2', fc='#dc3545', size=6.5)
t(ax, MW+MX-0.4, y0-1.32, '▾', size=9, ha='right', color='#888')

# Fila alerta 1
rect(ax, MX+0.1, y0-2.00, MW-0.2, 0.42, fc='#fff5f5', ec='#dee2e6', lw=0.4)
t(ax, MX+0.50, y0-1.79, '📅', size=9, color='#dc3545')
t(ax, MX+0.95, y0-1.79, 'Proyecto Edificio Central', size=7.5, bold=True)
t(ax, MX+3.50, y0-1.79, '— En Progreso', size=7.5, color='#888')
t(ax, MW+MX-2.4, y0-1.79, '01/03/2026', size=7.5, color='#dc3545', bold=True)
badge(ax, MW+MX-1.5, y0-1.91, 0.70, 0.24, 'Hoy', fc='#dc3545', size=6.5)
rounded(ax, MW+MX-0.70, y0-1.91, 0.50, 0.24, fc='none', ec='#dc3545', lw=0.7, pad=0.02)
t(ax, MW+MX-0.45, y0-1.79, 'Ver', size=7, ha='center', color='#dc3545')

# Accordion: Próximos a Vencer (colapsado)  — espacio extra arriba
rect(ax, MX+0.1, y0-2.55, MW-0.2, 0.42, fc='white', ec='#dee2e6', lw=0.8)
t(ax, MX+0.35, y0-2.34, '⏳  Próximos a Vencer', size=8.5, bold=True, color='#e6a817')
badge(ax, MX+4.30, y0-2.45, 0.38, 0.22, '1', fc='#ffc107', tc='#111', size=6.5)
t(ax, MW+MX-0.4, y0-2.34, '▸', size=9, ha='right', color='#888')

# ── KPI Cards — Proyectos ──────────────────────────────────────────────────────
t(ax, MX+0.15, y0-2.95, 'RESUMEN DE PROYECTOS', size=7, bold=True, color='#6c757d')

kpis = [
    ('12',  'Proyectos Totales', '#1B4D90', '📁'),
    ('5',   'En Progreso',       '#0d6efd', '🔄'),
    ('4',   'Completados',       '#198754', '✅'),
    ('3',   'Pendientes',        '#ffc107', '⏳'),
]
kw = (MW - 0.50) / 4
for i, (val, lbl, color, icon) in enumerate(kpis):
    kx = MX + 0.15 + i * (kw + 0.10)
    rect(ax, kx, y0-4.15, kw, 1.0, fc='white', ec='#dee2e6', lw=0.8)
    ax.plot([kx, kx], [y0-4.15, y0-3.15], color=color, linewidth=3.5, zorder=5)
    t(ax, kx+0.25, y0-3.47, val,  size=20, bold=True, color=color)
    t(ax, kx+0.25, y0-3.90, lbl,  size=7.5, color='#6c757d')
    t(ax, kx+kw-0.35, y0-3.47, icon, size=16, ha='center', color=color+'55')

# ── KPI Cards — Financiero ────────────────────────────────────────────────────
t(ax, MX+0.15, y0-4.40, 'RESUMEN FINANCIERO', size=7, bold=True, color='#6c757d')

kpis2 = [
    ('Bs. 45,700', 'Monto Total Proyectos', '#0F2D5A', '💰'),
    ('Bs. 28,200', 'Total Cobrado',         '#198754', '✔'),
    ('Bs. 17,500', 'Por Cobrar',            '#dc3545', '⚠'),
    ('8',          'Clientes Activos',      '#0dcaf0', '👥'),
]
for i, (val, lbl, color, icon) in enumerate(kpis2):
    kx = MX + 0.15 + i * (kw + 0.10)
    rect(ax, kx, y0-5.60, kw, 1.0, fc='white', ec='#dee2e6', lw=0.8)
    ax.plot([kx, kx], [y0-5.60, y0-4.60], color=color, linewidth=3.5, zorder=5)
    t(ax, kx+0.25, y0-4.92, val,  size=11, bold=True, color=color)
    t(ax, kx+0.25, y0-5.35, lbl,  size=7.5, color='#6c757d')
    t(ax, kx+kw-0.35, y0-4.92, icon, size=14, ha='center', color=color+'55')

# ── Gráficos ──────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-5.88, 'ANÁLISIS VISUAL', size=7, bold=True, color='#6c757d')

CHART_Y_TOP = y0 - 6.08
CHART_H     = 2.70
CHART_W     = (MW - 0.45) / 2

# ── Gráfico 1: Donut — Estado de Proyectos ───────────────────────────────────
cx1 = MX + 0.15
rect(ax, cx1, CHART_Y_TOP - CHART_H, CHART_W, CHART_H,
     fc='white', ec='#dee2e6', lw=0.8)
t(ax, cx1 + CHART_W/2, CHART_Y_TOP - 0.24,
  'Estado de Proyectos', size=8, bold=True, ha='center', color='#333')

center_x = cx1 + CHART_W / 2
center_y = CHART_Y_TOP - CHART_H / 2 - 0.05
R_OUT, R_IN = 0.78, 0.44

states = [
    ('En Progreso', 5 / 12, '#0d6efd'),
    ('Completados', 4 / 12, '#198754'),
    ('Pendientes',  3 / 12, '#ffc107'),
]
start_ang = 90
for label, frac, color in states:
    end_ang = start_ang - frac * 360
    w = patches.Wedge(
        (center_x, center_y), R_OUT, end_ang, start_ang,
        width=R_OUT - R_IN,
        facecolor=color, edgecolor='white', linewidth=1.5, zorder=4
    )
    ax.add_patch(w)
    mid_ang = (start_ang + end_ang) / 2
    lx = center_x + (R_OUT + 0.18) * math.cos(math.radians(mid_ang))
    ly = center_y + (R_OUT + 0.18) * math.sin(math.radians(mid_ang))
    t(ax, lx, ly, f'{int(frac * 12)}', size=7.5, bold=True,
      ha='center', color=color)
    start_ang = end_ang

# Texto central del donut
t(ax, center_x, center_y + 0.12, '12',    size=13, bold=True, ha='center', color='#333')
t(ax, center_x, center_y - 0.18, 'Total', size=6.5, ha='center', color='#888')

# Leyenda del donut
leg_y = CHART_Y_TOP - CHART_H + 0.35
for j, (label, _, color) in enumerate(states):
    lx_leg = cx1 + 0.18 + j * (CHART_W / 3)
    rect(ax, lx_leg, leg_y - 0.07, 0.14, 0.14, fc=color, ec='none', lw=0)
    t(ax, lx_leg + 0.20, leg_y, label, size=6.2, color='#555')

# ── Gráfico 2: Barras — Ingresos por Mes ─────────────────────────────────────
cx2 = MX + 0.15 + CHART_W + 0.35
rect(ax, cx2, CHART_Y_TOP - CHART_H, CHART_W, CHART_H,
     fc='white', ec='#dee2e6', lw=0.8)
t(ax, cx2 + CHART_W/2, CHART_Y_TOP - 0.24,
  'Ingresos por Mes (Bs.)', size=8, bold=True, ha='center', color='#333')

bar_data  = [('Nov', 8200), ('Dic', 12500), ('Ene', 9800),
             ('Feb', 15300), ('Mar', 18500), ('Abr', 11200)]
BAX  = cx2 + 0.42            # x inicio área de barras
BAY  = CHART_Y_TOP - CHART_H + 0.52   # y base
BAW  = CHART_W - 0.65        # ancho total área
BAH  = CHART_H - 0.90        # alto total área
MVAL = 20000
bw   = BAW / len(bar_data) - 0.07

# Líneas de grilla horizontales
for g in [0.25, 0.5, 0.75, 1.0]:
    gy = BAY + g * BAH
    ax.plot([BAX, BAX + BAW], [gy, gy],
            color='#e9ecef', linewidth=0.6, zorder=2)
    t(ax, BAX - 0.10, gy, f'{int(g * MVAL / 1000)}k',
      size=5.5, ha='right', color='#aaa')

# Barras
for j, (month, val) in enumerate(bar_data):
    bx = BAX + j * (bw + 0.07)
    bh = (val / MVAL) * BAH
    col = '#198754' if month == 'Mar' else AZUL
    rect(ax, bx, BAY, bw, bh, fc=col, ec='none', lw=0, z=3)
    t(ax, bx + bw/2, BAY - 0.13, month,
      size=6.0, ha='center', color='#888')
    t(ax, bx + bw/2, BAY + bh + 0.07, f'{val // 1000}k',
      size=5.5, ha='center', color='#555')

# Línea base
ax.plot([BAX, BAX + BAW], [BAY, BAY],
        color='#dee2e6', linewidth=0.9, zorder=3)

# ── Últimos Proyectos ─────────────────────────────────────────────────────────
PROJ_LABEL_Y = CHART_Y_TOP - CHART_H - 0.30
t(ax, MX+0.15, PROJ_LABEL_Y, 'Últimos Proyectos', size=9, bold=True, color='#333')

HDR_Y = PROJ_LABEL_Y - 0.42
rect(ax, MX+0.1, HDR_Y - 0.14, MW-0.2, 0.34, fc='#e9ecef', ec='#dee2e6', lw=0.7)
for lbl, cx in [('Nombre', 0.20), ('Cliente', 2.80), ('Estado', 5.30),
                ('Monto', 7.20), ('Fecha', 8.80)]:
    t(ax, MX+cx, HDR_Y + 0.03, lbl.upper(), size=6.5, bold=True, color='#555')

filas = [
    ('Seg. Edificio Central', 'Juan Pérez', 'En Progreso', '#0d6efd', 'Bs. 18,500', '01/03/2026'),
    ('CCTV Almacén Norte',    'Ana Flores', 'Completado',  '#198754', 'Bs.  9,200', '15/01/2026'),
    ('Alarmas Oficina Sur',   'C. Mamani',  'Pendiente',   '#ffc107', 'Bs. 12,000', '10/04/2026'),
]
for i, (nom, cli, est, ec, monto, fecha) in enumerate(filas):
    yr = HDR_Y - 0.35 - i * 0.40
    fc_r = 'white' if i % 2 == 0 else '#f8f9fa'
    rect(ax, MX+0.1, yr - 0.20, MW-0.2, 0.38, fc=fc_r, ec='#dee2e6', lw=0.4)
    t(ax, MX+0.20, yr, nom,   size=7.5, bold=True, color='#222')
    t(ax, MX+2.80, yr, cli,   size=7.5, color='#555')
    badge(ax, MX+5.20, yr-0.13, 1.0, 0.26, est,
          fc=ec, tc='white' if est != 'Pendiente' else '#111', size=6.5)
    t(ax, MX+7.20, yr, monto, size=7.5, color='#333')
    t(ax, MX+8.80, yr, fecha, size=7.5, color='#888')

draw_caption(ax, 'Figura XX: Panel de Control — Sistema SOBOTEC S.R.L.', W=W, H=H)
save(fig, 'wf_02_dashboard.png')
