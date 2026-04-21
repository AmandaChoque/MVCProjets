import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(13, 9))
ax.set_xlim(0, 13)
ax.set_ylim(0, 9)
ax.axis('off')
fig.patch.set_facecolor('white')

# ─── Helpers ───────────────────────────────────────────────────────────────

def rect(x, y, w, h, fc='white', ec='black', lw=1.0, radius=0):
    if radius:
        box = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad={radius}",
            linewidth=lw, edgecolor=ec, facecolor=fc
        )
    else:
        box = patches.Rectangle(
            (x, y), w, h,
            linewidth=lw, edgecolor=ec, facecolor=fc
        )
    ax.add_patch(box)

def text(x, y, s, size=8, bold=False, ha='left', va='center', color='black', italic=False):
    style = 'italic' if italic else 'normal'
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, s, fontsize=size, fontweight=weight, fontstyle=style,
            ha=ha, va=va, color=color)

def hline(x0, x1, y, lw=0.5, color='#aaa'):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw)

def btn(x, y, w, h, label, size=7.5):
    rect(x, y, w, h, fc='#d8d8d8', ec='#555', lw=0.8)
    text(x + w/2, y + h/2, label, size=size, ha='center')

# ─── Barra del navegador ────────────────────────────────────────────────────
rect(0, 8.55, 13, 0.45, fc='#e0e0e0', ec='#888')
text(0.3, 8.78, '< >', size=8, color='#555')
rect(0.9, 8.62, 8.5, 0.28, fc='white', ec='#aaa', lw=0.7)
text(1.0, 8.76, 'http://localhost:8000/projects/1/view/', size=7, color='#444')
text(11.5, 8.78, 'Usuario ▾', size=7.5, ha='center', color='#333')

# ─── Ventana principal ──────────────────────────────────────────────────────
rect(0, 0, 13, 8.55, fc='#f4f4f4', ec='#888', lw=1.2)

# ─── Sidebar ────────────────────────────────────────────────────────────────
rect(0, 0, 2.6, 8.55, fc='#2b2b2b', ec='#111', lw=1.0)
text(1.3, 8.25, 'SOBOTEC', size=10, bold=True, ha='center', color='white')
hline(0.15, 2.45, 8.05, color='#555')

menu = [
    ('Dashboard',    False),
    ('Proyectos',    True),   # activo
    ('Clientes',     False),
    ('Empleados',    False),
    ('Inventario',   False),
    ('Pagos',        False),
    ('Reportes',     False),
]
for i, (label, activo) in enumerate(menu):
    y = 7.65 - i * 0.55
    fc = '#4a4a4a' if activo else '#2b2b2b'
    rect(0.1, y - 0.18, 2.4, 0.38, fc=fc, ec='none')
    color = 'white' if activo else '#cccccc'
    text(0.45, y, f'  {label}', size=8.2, ha='left', va='center', color=color)

# ─── Contenido principal ─────────────────────────────────────────────────────
# Título
text(2.9, 8.2, 'Detalle del Proyecto', size=11, bold=True, color='#222')
hline(2.75, 12.85, 7.95, lw=0.8, color='#bbb')

# ── Sección: Info del proyecto ───────────────────────────────────────────────
rect(2.8, 5.55, 9.9, 2.25, fc='white', ec='#ccc', lw=0.8)
text(3.05, 7.6, 'Información General', size=9, bold=True, color='#333')
hline(3.0, 12.6, 7.42, lw=0.5, color='#ddd')

# Columna izquierda
campos_izq = [
    ('Nombre del Proyecto:', 'Proyecto Seguridad Edificio Central'),
    ('Estado:', 'En Progreso'),
    ('Tipo:', 'Instalación Nueva'),
]
for i, (label, val) in enumerate(campos_izq):
    y = 7.1 - i * 0.5
    text(3.1, y, label, size=7.5, bold=True, color='#555')
    rect(3.1, y - 0.32, 4.2, 0.28, fc='#f7f7f7', ec='#ccc', lw=0.6)
    text(3.22, y - 0.18, val, size=7.5, color='#222')

# Columna derecha
campos_der = [
    ('Cliente:', 'Juan Pérez García'),
    ('Fecha Inicio:', '01/03/2026'),
    ('Monto Total:', 'Bs. 18,500.00'),
]
for i, (label, val) in enumerate(campos_der):
    y = 7.1 - i * 0.5
    text(7.9, y, label, size=7.5, bold=True, color='#555')
    rect(7.9, y - 0.32, 4.6, 0.28, fc='#f7f7f7', ec='#ccc', lw=0.6)
    text(8.02, y - 0.18, val, size=7.5, color='#222')

# ── Botones de acción ─────────────────────────────────────────────────────────
btn(2.8,  5.05, 2.1, 0.38, 'Editar Proyecto')
btn(5.05, 5.05, 2.1, 0.38, 'Completar')
btn(7.30, 5.05, 2.1, 0.38, 'Agregar Sede')
btn(9.55, 5.05, 2.1, 0.38, 'Desactivar')

# ── Sección: Sedes ──────────────────────────────────────────────────────────
text(2.9, 4.7, 'Sedes de Instalación', size=9, bold=True, color='#333')
hline(2.75, 12.85, 4.52, lw=0.5, color='#bbb')

# Cabecera tabla
rect(2.8, 4.05, 9.9, 0.38, fc='#d5d5d5', ec='#aaa', lw=0.7)
cols_sede = [('Nombre', 3.2), ('Dirección', 5.6), ('% Avance', 8.8), ('Estado', 10.2), ('Acciones', 11.4)]
for label, x in cols_sede:
    text(x, 4.24, label, size=7.5, bold=True, ha='center')

# Filas tabla
sedes = [
    ('Sede Principal', 'Av. Arce #123, La Paz', '75%', 'Activa'),
    ('Sede Norte',     'C. Potosí #45, La Paz',  '30%', 'Activa'),
]
for i, (nombre, dir_, pct, estado) in enumerate(sedes):
    y = 3.65 - i * 0.38
    fc_row = 'white' if i % 2 == 0 else '#f7f7f7'
    rect(2.8, y - 0.15, 9.9, 0.35, fc=fc_row, ec='#ccc', lw=0.5)
    text(3.2,  y + 0.02, nombre,  size=7, ha='center')
    text(5.6,  y + 0.02, dir_,    size=7, ha='center')
    text(8.8,  y + 0.02, pct,     size=7, ha='center')
    text(10.2, y + 0.02, estado,  size=7, ha='center')
    text(11.4, y + 0.02, '[Ver] [Editar]', size=7, ha='center', color='#444')

# ── Sección: Equipo ───────────────────────────────────────────────────────────
text(2.9, 2.7, 'Equipo del Proyecto', size=9, bold=True, color='#333')
hline(2.75, 12.85, 2.52, lw=0.5, color='#bbb')

equipo = ['Carlos Mamani  (Instalador)', 'Ana Flores  (Técnica)', 'Luis Quispe  (Instalador)']
for i, nombre in enumerate(equipo):
    x = 2.85 + i * 3.4
    rect(x, 2.05, 3.1, 0.35, fc='#e8e8e8', ec='#aaa', lw=0.7, radius=0.04)
    text(x + 1.55, 2.22, nombre, size=7.2, ha='center')

# ── Sección: Pagos (mini) ─────────────────────────────────────────────────────
text(2.9, 1.7, 'Pagos del Proyecto', size=9, bold=True, color='#333')
hline(2.75, 12.85, 1.52, lw=0.5, color='#bbb')

rect(2.8, 0.7, 9.9, 0.7, fc='white', ec='#ccc', lw=0.7)
text(3.1, 1.26, 'Monto Pagado:', size=7.5, bold=True, color='#555')
text(4.8, 1.26, 'Bs. 9,000.00', size=7.5, color='#222')
text(7.0, 1.26, 'Estado de Pago:', size=7.5, bold=True, color='#555')
text(8.9, 1.26, 'Parcial', size=7.5, color='#222')
text(3.1, 0.9,  'Pendiente:', size=7.5, bold=True, color='#555')
text(4.8, 0.9,  'Bs. 9,500.00', size=7.5, color='#222')
btn(10.2, 0.75, 2.3, 0.55, 'Registrar Pago')

# ─── Pie / caption ────────────────────────────────────────────────────────────
text(6.5, 0.18, 'Figura XX: Vista de Detalle de Proyecto — Sistema SOBOTEC S.R.L.',
     size=8.5, ha='center', italic=True, color='#444')

plt.tight_layout(pad=0)
plt.savefig('wireframes/wireframe_detalle_proyecto.png',
            dpi=160, bbox_inches='tight', facecolor='white')
plt.show()
print("Guardado en: wireframes/wireframe_detalle_proyecto.png")
