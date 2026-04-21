# Diagrama de Contenido UWE — SOBOTEC S.R.L.

```mermaid
classDiagram
    direction TB

    %% ══════════════════════════════════════════
    %%  MÓDULO PROYECTOS
    %% ══════════════════════════════════════════

    class Cliente {
        +nit_ci : String
        +nombre : String
        +apellido_paterno : String
        +apellido_materno : String
        +rol_contacto : propietario|representante|gerente|presidente_zona|encargado
        +tipo_contratante : empresa|personal|entidad_publica
        +telefono : String
        +correo : Email
        +direccion : String
        +nombre_entidad : String
        +representante_legal : String
        +activo : Boolean
    }

    class Proyecto {
        +codigo : String
        +nombre : String
        +descripcion : Text
        +estado_proyecto : pendiente|en_progreso|completado
        +tipo_proyecto : instalacion_nueva|ampliacion|mantenimiento_externo|emergencia
        +estado_pago : no_pagado|parcial|pagado
        +monto_total : Decimal
        +fecha_inicio : Date
        +fecha_fin : Date
        +observacion : Text
    }

    class ContratoProyecto {
        +fecha_firma : Date
        +fecha_inicio : Date
        +fecha_fin : Date
        +monto_acordado : Decimal
        +porcentaje_multa_diaria : Decimal
        +porcentaje_multa_maxima : Decimal
        +garantia_meses : Integer
        +observaciones : Text
        +documento : File
    }

    class HistorialPresupuesto {
        +monto_anterior : Decimal
        +monto_actual : Decimal
        +motivo_cambio : Text
        +fecha_modificacion : DateTime
    }

    class PagoProyecto {
        +monto : Decimal
        +descuento : Decimal
        +motivo_descuento : String
        +fecha : Date
        +tipo_pago : efectivo|transferencia
        +numero_referencia : String
    }

    class Sede {
        +nombre : String
        +direccion : String
        +descripcion : Text
        +latitud : Decimal
        +longitud : Decimal
        +estado : pendiente|en_progreso|completado
    }

    class TareaChecklist {
        +descripcion : String
        +orden : Integer
        +completado : Boolean
        +fecha_completado : DateTime
    }

    class FotoSede {
        +foto : Image
        +descripcion : String
    }

    class PlantillaTarea {
        +nombre : String
        +tipo : camara_ip|camara_analogica|dvr_nvr|alarma|sensor|otro
        +descripcion : Text
    }

    class ItemPlantilla {
        +descripcion : String
        +orden : Integer
    }

    class Notificacion {
        +tipo : sede_completada|tarea_completada|general
        +mensaje : Text
        +leida : Boolean
        +fecha : DateTime
    }

    %% ══════════════════════════════════════════
    %%  MÓDULO EMPLEADOS
    %% ══════════════════════════════════════════

    class Empleado {
        +username : String
        +nombre : String
        +apellido_paterno : String
        +apellido_materno : String
        +cargo : administrador|gerente|instalador|tecnico_soporte|secretaria
        +carnet_identidad : String
        +numero_celular : String
    }

    class ContratoEmpleado {
        +dias_laborales : Integer
        +fecha_firma : Date
        +fecha_inicio : Date
        +fecha_fin : Date
        +monto_acordado : Decimal
        +observaciones : Text
        +documento : File
    }

    class PagoEmpleado {
        +monto : Decimal
        +fecha : Date
        +tipo_pago : efectivo|transferencia
        +concepto : pago_jornada|adelanto|liquidacion|dia_extra|otro
    }

    class JornadaEmpleado {
        +fecha : Date
        +dias : 0.5|1.0
        +estado : pendiente|aprobada|rechazada
        +observacion : Text
        +motivo_rechazo : Text
    }

    %% ══════════════════════════════════════════
    %%  MÓDULO INVENTARIO
    %% ══════════════════════════════════════════

    class Proveedor {
        +nombre : String
        +rubro : camaras|cables|equipos_red|alarmas|sensores|computo|otro
        +nit : String
        +telefono : String
        +correo : Email
        +direccion : String
        +encargado_nombre : String
        +encargado_cargo : String
        +encargado_celular : String
    }

    class Insumo {
        +nombre : String
        +marca : String
        +modelo : String
        +categoria : camara_ip|camara_analogica|nvr_dvr|alarma|sensor|cable|...
        +unidad_medida : unidad|metro|rollo|caja|par
        +stock : Integer
        +stock_minimo : Integer
        +ultimo_precio_compra : Decimal
    }

    class Requiere {
        +cantidad : Integer
    }

    class Compra {
        +cantidad : Integer
        +costo_unitario : Decimal
        +fecha : Date
        +numero_factura : String
    }

    class RequiereLote {
        +cantidad : Integer
    }

    %% ══════════════════════════════════════════
    %%  RELACIONES — MÓDULO PROYECTOS
    %% ══════════════════════════════════════════

    Cliente "1" --> "0..*" Proyecto : contrata
    Proyecto "1" *-- "0..1" ContratoProyecto : formalizado en
    Proyecto "1" *-- "0..*" PagoProyecto : cobrado en
    Proyecto "1" *-- "0..*" HistorialPresupuesto : historial de
    Proyecto "1" *-- "0..*" Sede : punto de instalación
    Proyecto "0..*" --> "0..*" Notificacion : genera
    Sede "1" *-- "0..*" TareaChecklist : checklist
    Sede "1" *-- "0..*" FotoSede : evidencia
    Sede "0..*" --> "0..1" PlantillaTarea : basada en
    PlantillaTarea "1" *-- "1..*" ItemPlantilla : contiene
    TareaChecklist "0..*" --> "0..*" Empleado : participantes
    TareaChecklist "0..*" --> "0..1" Empleado : completado por
    FotoSede "0..*" --> "0..1" Empleado : subida por
    Notificacion "0..*" --> "1" Empleado : destinatario

    %% ══════════════════════════════════════════
    %%  RELACIONES — MÓDULO EMPLEADOS
    %% ══════════════════════════════════════════

    Empleado "1" *-- "0..*" ContratoEmpleado : contratado en
    Empleado "0..*" --> "0..*" Proyecto : equipo del proyecto
    Empleado "1" --> "0..*" Proyecto : creado por
    ContratoEmpleado "1" *-- "0..*" PagoEmpleado : pagado en
    ContratoEmpleado "1" *-- "0..*" JornadaEmpleado : jornadas
    JornadaEmpleado "0..*" --> "1" Proyecto : trabajado en
    JornadaEmpleado "0..*" --> "0..1" PagoEmpleado : cubierta por
    JornadaEmpleado "0..*" --> "0..1" Empleado : registrado por

    %% ══════════════════════════════════════════
    %%  RELACIONES — MÓDULO INVENTARIO
    %% ══════════════════════════════════════════

    Proveedor "1" --> "0..*" Compra : provee en
    Insumo "1" --> "0..*" Compra : adquirido en
    Proyecto "1" --> "0..*" Requiere : necesita
    Insumo "1" --> "0..*" Requiere : requerido como
    Requiere "1" *-- "0..*" RequiereLote : trazabilidad FIFO
    Compra "1" --> "0..*" RequiereLote : consumido en
```

## Leyenda

| Símbolo | Significado |
|---|---|
| `*--` | Composición (el hijo no existe sin el padre) |
| `-->` | Asociación / referencia |
| `"1"` `"0..*"` | Multiplicidades |

## Módulos del sistema

| Módulo | Clases de contenido |
|---|---|
| **Proyectos** | Cliente, Proyecto, ContratoProyecto, HistorialPresupuesto, PagoProyecto, Sede, TareaChecklist, FotoSede, PlantillaTarea, ItemPlantilla, Notificacion |
| **Empleados** | Empleado, ContratoEmpleado, PagoEmpleado, JornadaEmpleado |
| **Inventario** | Proveedor, Insumo, Requiere, Compra, RequiereLote |
