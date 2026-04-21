"""Ejecuta todos los wireframes en secuencia."""
import subprocess, sys

scripts = [
    'wireframes/wf_01_login.py',
    'wireframes/wf_02_dashboard.py',
    'wireframes/wf_03_editar_proyecto.py',
    'wireframes/wf_04_vista_proyecto.py',
    'wireframes/wf_05_clientes.py',
    'wireframes/wf_06_crear_cliente.py',
    'wireframes/wf_07_empleados.py',
    'wireframes/wf_08_insumos.py',
    'wireframes/wf_09_pagos.py',
    'wireframes/wireframe_lista_proyectos.py',
]

for s in scripts:
    print(f'\n{"="*50}\n▶ {s}\n{"="*50}')
    result = subprocess.run([sys.executable, s], capture_output=False)
    if result.returncode != 0:
        print(f'  ❌ Error en {s}')
    else:
        print(f'  ✅ OK')

print('\n✅ Todos los wireframes generados en wireframes/')
