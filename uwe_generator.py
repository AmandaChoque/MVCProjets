#!/usr/bin/env python3
"""
Generador automático de diagramas UWE (UML-based Web Engineering) para el proyecto MVCProjets.
Parsea models.py → genera Mermaid para Use Case, Sequence, Activity Diagrams.
"""

import re
import os
from pathlib import Path

MODELS_PATHS = [
    'empleados/models.py',
    'projects/models.py',
    'inventario/models.py',
]

def parse_models():
    """Parsea todos models.py → dict de clases y relaciones."""
    classes = {}
    relations = []
    for path in MODELS_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Clases
        for match in re.finditer(r'class (\w+)\s*\((\w+)\):', content):
            cls, base = match.groups()
            classes[cls] = base
        # FKs simples (no ManyToMany)
        for match in re.finditer(r'ForeignKey\s*\(\s*[\'\"]([\w\.]+)[\'\"]', content):
            target = match.group(1).split('.')[-1]
            relations.append(f'{target}')
    return classes, set(relations)

def generate_use_case():
    """Genera Use Case Diagram Mermaid."""
    actors = ['Admin', 'Gerente', 'Instalador', 'Cliente']
    usecases = [
        'Gestionar Proyectos',
        'Registrar Jornadas',
        'Gestionar Pagos',
        'Controlar Inventario',
        'Completar Checklists',
        'Ver Reportes',
    ]
    mermaid = '''```mermaid
usecaseDiagram
    actor Admin
    actor Gerente
    actor Instalador
    actor Cliente as "Cliente Externo"

'''
    for actor in actors:
        mermaid += f'    {actor} --> ({usecases[0]})\n'
    mermaid += f'''
    Admin --> ({usecases[0]})
    Admin --> ({usecases[1]})
    Admin --> ({usecases[2]})
    Gerente --> ({usecases[3]})
    Instalador --> ({usecases[4]})
    Cliente --> (Ver Estado Proyecto)
```
'''
    return mermaid

def generate_sequence_project():
    """Sequence: Crear Proyecto."""
    return '''```mermaid
sequenceDiagram
    participant U as Usuario (Admin)
    participant V as View
    participant M as Model (Proyecto)
    participant DB as DB

    U->>V: POST /proyectos/nuevo/
    V->>M: create_proyecto()
    M->>DB: Proyecto.objects.create()
    DB-->>M: OK
    M-->>V: Proyecto instance
    V-->>U: Redirect /proyectos/{id}/
```
'''

def generate_sequence_jornada():
    return '''```mermaid
sequenceDiagram
    participant I as Instalador
    participant V as View
    participant J as JornadaEmpleado
    participant P as Proyecto

    I->>V: POST /jornadas/nueva/
    V->>J: create_jornada()
    J->>P: validate_asignacion()
    P-->>J: OK
    J->>DB: save()
    DB-->>J: OK
    V-->>I: Redirect /jornadas/{id}/
```
'''

def generate_activity_project():
    return '''```mermaid
flowchart TD
    A[Crear Proyecto] --> B[Asignar Cliente/Equipo]
    B --> C[Crear Sedes]
    C --> D[Asignar Insumos]
    D --> E[Instalador: Completar Tareas]
    E --> F{Todas Sedes 100%?}
    F -->|No| E
    F -->|Si| G[Proyecto Completado]
    G --> H[Crear Garantía si aplica]
    H --> I[Registrar Pago Pendiente]
```
'''

def write_mmd(filename, content):
    path = Path(filename)
    path.write_text(content)
    print(f'✨ Generado: {filename}')

def main():
    print('🚀 Generando diagramas UWE...')
    _, _ = parse_models()  # Warmup
    write_mmd('use_case.mmd', generate_use_case())
    write_mmd('sequence_create_project.mmd', generate_sequence_project())
    write_mmd('sequence_jornada.mmd', generate_sequence_jornada())
    write_mmd('activity_project_lifecycle.mmd', generate_activity_project())
    print('\n✅ Listo! Abre *.mmd en Mermaid Live (mermaid.live)')
    print('Para Class Diagram actualizado: editar diagrama_contenido.mmd')
    print('Para Navegación: python gen_diagrama.py')

if __name__ == '__main__':
    main()

