"""Wireframe 04 — Vista de Proyecto (project_view.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 10
fig, ax = new_fig(W, H)
y0  = draw_navbar(ax, W, H)
MX  = draw_sidebar(ax, H, active='proyectos')
MW  = W - MX - 0.2
rect(ax, MX, 0, MW, y0, fc=BG, ec='none', lw=0)

# ── Encabezado ────────────────────────────────────────────────────────────────
t(ax, MX+0.15, y0-0.38, 'Seg. Edificio Central', size=12, bold=True, color=AZUL)
# Badges
badge(ax, MX+0.15, y0-0.82, 0.7, 0.26, 'PR-001',       fc='#6c757d', size=6.5)
badge(ax, MX+0.98, y0-0.82, 1.1, 0.26, 'En Progreso',  fc='#0d6efd', size=6.5)
badge(ax, MX+2.22, y0-0.82, 1.0, 0.26, 'Pago Parcial', fc='#0dcaf0', tc='#111', size=6.5)
t(ax, MX+3.42, y0-0.69, '| Monto: Bs. 18,500.00', size=8, color='#555')

# Botones derecha
btn(ax, W-5.5, y0-0.88, 1.3, 0.34, '← Volver',    fc='white', tc='#555', ec='#bbb')
btn(ax, W-4.0, y0-0.88, 1.4, 0.34, '📄 Ficha PDF', fc='white', tc='#dc3545', ec='#dc3545')
btn(ax, W-2.4, y0-0.88, 1.6, 0.34, '✏ Editar',    fc=AZUL)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tabs = ['General', 'Progreso  75%', 'Contratos', 'Sedes  2', 'Insumos  5', 'Equipo  3', 'Finanzas']
tx = MX + 0.1
for i, tab in enumerate(tabs):
    active = i == 0
    fc = 'white' if active else BG
    rect(ax, tx, y0-1.45, len(tab)*0.13+0.4, 0.44,
         fc=fc, ec='#dee2e6', lw=0.8)
    color = '#0d6efd' if active else '#6c757d'
    t(ax, tx + (len(tab)*0.13+0.4)/2, y0-1.23,
      tab, size=7.8, ha='center', bold=active, color=color)
    if active:
        ax.plot([tx, tx+len(tab)*0.13+0.4], [y0-1.45, y0-1.45],
                color='#0d6efd', linewidth=2, zorder=5)
    tx += len(tab)*0.13 + 0.5

# ── Contenido Tab General ─────────────────────────────────────────────────────
rect(ax, MX+0.1, 0.55, MW-0.2, y0-2.0, fc='white', ec='#dee2e6', lw=0.8)

# Sección info general
t(ax, MX+0.4, y0-2.2, 'Información General', size=9, bold=True, color='#333')
hline(ax, MX+0.3, W-0.4, y0-2.42, color='#eee', lw=0.8)

info_izq = [
    ('Nombre:', 'Proyecto Seg. Edificio Central'),
    ('Código:', 'PR-001'),
    ('Tipo:', 'Instalación Nueva'),
    ('Estado:', 'En Progreso'),
    ('Cliente:', 'Juan Pérez García'),
]
info_der = [
    ('Fecha Inicio:', '01/03/2026'),
    ('Fecha Fin:', '— (en curso)'),
    ('Monto Total:', 'Bs. 18,500.00'),
    ('Estado Pago:', 'Pago Parcial'),
    ('Creado por:', 'admin'),
]

LX, RX = MX+0.4, MX+5.8
for i, (lbl, val) in enumerate(info_izq):
    y = y0 - 2.8 - i*0.52
    t(ax, LX, y, lbl, size=8, bold=True, color='#495057')
    t(ax, LX+1.8, y, val, size=8, color='#333')
for i, (lbl, val) in enumerate(info_der):
    y = y0 - 2.8 - i*0.52
    t(ax, RX, y, lbl, size=8, bold=True, color='#495057')
    t(ax, RX+1.8, y, val, size=8, color='#333')

# Descripción
t(ax, MX+0.4, y0-5.65, 'Descripción:', size=8, bold=True, color='#495057')
rect(ax, MX+0.4, y0-6.45, MW-0.7, 0.65, fc='#f8f9fa', ec='#dee2e6', lw=0.6)
t(ax, MX+0.6, y0-6.12, 'Instalación de sistema de videovigilancia en edificio central.',
  size=7.5, color='#555', italic=True)

# Observaciones
t(ax, MX+0.4, y0-6.75, 'Observaciones:', size=8, bold=True, color='#495057')
rect(ax, MX+0.4, y0-7.42, MW-0.7, 0.55, fc='#f8f9fa', ec='#dee2e6', lw=0.6)
t(ax, MX+0.6, y0-7.14, 'Coordinar con el personal de seguridad del edificio.',
  size=7.5, color='#555', italic=True)

draw_caption(ax, 'Figura XX: Vista de Proyecto — Sistema SOBOTEC S.R.L.', W=W)
save(fig, 'wf_04_vista_proyecto.png')
