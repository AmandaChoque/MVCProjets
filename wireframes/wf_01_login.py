"""Wireframe 01 — Inicio de Sesión (signin.html)"""
import sys; sys.path.insert(0, 'wireframes')
from helpers import *

W, H = 14, 9
fig, ax = new_fig(W, H)

# ── Panel izquierdo — branding (40%) ────────────────────────────────────────
rect(ax, 0, 0, 5.6, H, fc=AZUL, ec=AZUL_DARK, lw=0)

# Círculos decorativos
ax.add_patch(plt.Circle((5.6, H), 2.2, color='none',
             linestyle='-', linewidth=18,
             ec='#D4B84A18', fill=False))
ax.add_patch(plt.Circle((0, 0), 1.5, color='none',
             linewidth=14, ec='#D4B84A14', fill=False))

# Logo circular
ax.add_patch(plt.Circle((2.8, 6.2), 1.1,
             color='#ffffff10', linewidth=2.5,
             ec='#D4B84A66', fill=True))
t(ax, 2.8, 6.2, '▣', size=34, ha='center', va='center', color='white')

# Nombre empresa
t(ax, 2.8, 4.8, 'SOBOTEC S.R.L.', size=15, bold=True,
  ha='center', color=DORADO)

# Línea divisora dorada
ax.plot([1.8, 3.8], [4.45, 4.45], color=DORADO, linewidth=1.5, alpha=0.5)

# Descripción
t(ax, 2.8, 4.1, 'Sistema para la gestión de proyectos',
  size=8.5, ha='center', color='#ffffffaa', italic=True)

# Features
features = [
    '📷  Cámaras IP y analógicas',
    '🖥  DVR / NVR y redes',
    '🔔  Alarmas y sensores',
    '🔧  Instalación y mantenimiento',
]
for i, f in enumerate(features):
    t(ax, 1.2, 3.4 - i*0.48, f, size=8, color='#ffffffaa')

t(ax, 2.8, 0.8, 'BOLIVIA — LA PAZ', size=6.5, ha='center',
  color='#ffffff44', bold=True)

# ── Panel derecho — formulario (60%) ────────────────────────────────────────
rect(ax, 5.6, 0, 8.4, H, fc='white', ec='#eee', lw=0.5)


# Títulos
t(ax, 6.3, 6.6, 'Iniciar Sesión', size=14, bold=True, color='#111827')
t(ax, 6.3, 6.25, 'Ingresa tus credenciales para acceder al sistema',
  size=8, color='#9ca3af', italic=True)

# Campo Usuario
t(ax, 6.3, 5.75, 'Usuario', size=8, bold=True, color='#374151')
rounded(ax, 6.3, 5.28, 7.3, 0.38, fc='white', ec='#e2e8f0', lw=1.0, pad=0.03)
rounded(ax, 6.3, 5.28, 0.45, 0.38, fc='#f8fafc', ec='#e2e8f0', lw=1.0, pad=0.03)
t(ax, 6.52, 5.47, '👤', size=9, ha='center', color='#94a3b8')
t(ax, 6.85, 5.47, 'Nombre de usuario', size=8, color='#cbd5e1')

# Campo Contraseña
t(ax, 6.3, 4.9, 'Contraseña', size=8, bold=True, color='#374151')
rounded(ax, 6.3, 4.43, 7.3, 0.38, fc='white', ec='#e2e8f0', lw=1.0, pad=0.03)
rounded(ax, 6.3, 4.43, 0.45, 0.38, fc='#f8fafc', ec='#e2e8f0', lw=1.0, pad=0.03)
t(ax, 6.52, 4.62, '🔒', size=9, ha='center', color='#94a3b8')
t(ax, 6.85, 4.62, 'Contraseña', size=8, color='#cbd5e1')
# Ícono ojo
rounded(ax, 13.15, 4.43, 0.45, 0.38, fc='white', ec='#e2e8f0', lw=1.0, pad=0.03)
t(ax, 13.38, 4.62, '👁', size=9, ha='center', color='#94a3b8')

# Botón ingresar
rounded(ax, 6.3, 3.72, 7.3, 0.52,
        fc=AZUL, ec=AZUL_DARK, lw=0, pad=0.05)
t(ax, 9.95, 3.98, '→  Ingresar al Sistema', size=10,
  bold=True, ha='center', color='white')

# Botón volver
rounded(ax, 6.3, 3.08, 7.3, 0.46,
        fc='white', ec='#e2e8f0', lw=1.0, pad=0.04)
t(ax, 9.95, 3.31, '← Volver al inicio', size=9,
  ha='center', color='#6b7280')

# Footer
t(ax, 9.95, 2.55, '© 2026 SOBOTEC S.R.L. — Solo personal autorizado',
  size=7.5, ha='center', color='#94a3b8', italic=True)

# Marco y caption
draw_caption(ax, 'Figura XX: Inicio de Sesión — Sistema SOBOTEC S.R.L.', W=W, y=0.22)
save(fig, 'wf_01_login.png')
