from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase

from .models import Cliente, Proyecto, PagoProyecto
from .form import PaymentForm
from empleados.models import Empleado, ContratoEmpleado, JornadaEmpleado
from inventario.forms import InsumoForm, CompraForm
from inventario.models import Proveedor, Insumo


# ---------------------------------------------------------------------------
# Helpers reutilizables
# ---------------------------------------------------------------------------

def crear_empleado(username='testuser', cargo='administrador'):
    return Empleado.objects.create_user(
        username=username,
        password='pass1234',
        nombre='Test',
        apellido_paterno='User',
        carnet_identidad='1234560',
        cargo=cargo,
    )


def crear_cliente():
    return Cliente.objects.create(
        nombre='Ana',
        apellido_paterno='Lopez',
        nit_ci='1234567',
        tipo_contratante='personal',
        rol_contacto='propietario',
        telefono='70000001',
        direccion='Av. Siempre Viva',
    )


def crear_proyecto(empleado, monto_total='10000.00', estado='pendiente',
                   dias_retraso=0, multa_diaria='0', multa_maxima='20'):
    hoy = date.today()
    if dias_retraso > 0:
        fecha_fin_contrato = hoy - timedelta(days=dias_retraso)
    else:
        fecha_fin_contrato = hoy + timedelta(days=30)

    return Proyecto.objects.create(
        codigo='PRY-001',
        nombre='Instalacion SOBOTEC Test',
        estado_proyecto=estado,
        tipo_proyecto='instalacion_nueva',
        estado_pago='no_pagado',
        monto_total=Decimal(monto_total),
        creado_por=empleado,
        cliente=crear_cliente(),
        fecha_fin_contrato=fecha_fin_contrato,
        monto_acordado=Decimal(monto_total),
        porcentaje_multa_diaria=Decimal(multa_diaria),
        porcentaje_multa_maxima=Decimal(multa_maxima),
    )


# ===========================================================================
# 1. PaymentForm — clean_monto
# ===========================================================================

class PaymentFormCleanMontoTest(TestCase):
    """Valida que clean_monto acepte formatos correctos y rechace los incorrectos."""

    def setUp(self):
        self.empleado = crear_empleado()
        self.proyecto = crear_proyecto(self.empleado)

    def _data(self, monto):
        return {
            'monto': monto,
            'fecha': date.today().isoformat(),
            'tipo_pago': 'efectivo',
            'numero_referencia': '',
            'proyecto': self.proyecto.pk,
        }

    def test_monto_entero_valido(self):
        form = PaymentForm(data=self._data('1500'))
        form.is_valid()
        self.assertNotIn('monto', form.errors)

    def test_monto_decimal_dos_cifras_valido(self):
        form = PaymentForm(data=self._data('1500.50'))
        form.is_valid()
        self.assertNotIn('monto', form.errors)

    def test_monto_decimal_una_cifra_valido(self):
        form = PaymentForm(data=self._data('200.5'))
        form.is_valid()
        self.assertNotIn('monto', form.errors)

    def test_monto_retorna_decimal(self):
        form = PaymentForm(data=self._data('3500.75'))
        form.is_valid()
        self.assertEqual(form.cleaned_data['monto'], Decimal('3500.75'))

    def test_monto_con_coma_invalido(self):
        form = PaymentForm(data=self._data('1.500,00'))
        form.is_valid()
        self.assertIn('monto', form.errors)

    def test_monto_cero_invalido(self):
        form = PaymentForm(data=self._data('0'))
        form.is_valid()
        self.assertIn('monto', form.errors)

    def test_monto_negativo_invalido(self):
        form = PaymentForm(data=self._data('-500'))
        form.is_valid()
        self.assertIn('monto', form.errors)

    def test_monto_texto_invalido(self):
        form = PaymentForm(data=self._data('abc'))
        form.is_valid()
        self.assertIn('monto', form.errors)

    def test_monto_vacio_invalido(self):
        form = PaymentForm(data=self._data(''))
        form.is_valid()
        self.assertIn('monto', form.errors)


# ===========================================================================
# 2. Proyecto._sync_estado_pago — lógica de negocio y señal post_save
# ===========================================================================

class UpdatePaymentStatusTest(TestCase):
    """Verifica que el estado_pago del proyecto se actualice correctamente."""

    def setUp(self):
        self.empleado = crear_empleado()
        self.proyecto = crear_proyecto(self.empleado, monto_total='10000.00')

    def _pago(self, monto, activo=True):
        return PagoProyecto.objects.create(
            monto=Decimal(monto),
            fecha=date.today(),
            tipo_pago='efectivo',
            proyecto=self.proyecto,
            activo=activo,
        )

    def test_sin_pagos_es_no_pagado(self):
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'no_pagado')

    def test_pago_parcial_cambia_estado_a_parcial(self):
        self._pago('4000.00')
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'parcial')

    def test_pago_exacto_al_total_cambia_a_pagado(self):
        self._pago('10000.00')
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'pagado')

    def test_multiples_pagos_que_suman_el_total(self):
        self._pago('6000.00')
        self._pago('4000.00')
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'pagado')

    def test_pago_inactivo_no_cuenta_para_el_total(self):
        pago = self._pago('10000.00')
        pago.activo = False
        pago.save()
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertNotEqual(self.proyecto.estado_pago, 'pagado')

    def test_senal_post_save_actualiza_proyecto_automaticamente(self):
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'no_pagado')
        PagoProyecto.objects.create(
            monto=Decimal('10000.00'),
            fecha=date.today(),
            tipo_pago='efectivo',
            proyecto=self.proyecto,
            activo=True,
        )
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'pagado')

    def test_descuento_suma_al_total_cobrado(self):
        """Un pago con descuento debe contar monto + descuento para el estado_pago."""
        PagoProyecto.objects.create(
            monto=Decimal('9000.00'),
            descuento=Decimal('1000.00'),
            fecha=date.today(),
            tipo_pago='efectivo',
            proyecto=self.proyecto,
        )
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'pagado')


# ===========================================================================
# 3. Proyecto — cálculo de multas (campos absorbidos del contrato)
# ===========================================================================

class ProyectoMultaTest(TestCase):
    """Verifica el cálculo de días de retraso, multa acumulada y estado_multa."""

    def setUp(self):
        self.empleado = crear_empleado()

    def test_sin_retraso_estado_normal(self):
        proyecto = crear_proyecto(self.empleado, dias_retraso=0)
        self.assertEqual(proyecto.estado_multa, 'normal')
        self.assertEqual(proyecto.dias_retraso, 0)

    def test_con_retraso_estado_en_multa(self):
        proyecto = crear_proyecto(self.empleado, dias_retraso=5,
                                   multa_diaria='0.50', multa_maxima='10.00')
        self.assertEqual(proyecto.estado_multa, 'en_multa')
        self.assertGreater(proyecto.dias_retraso, 0)

    def test_multa_acumulada_calculo(self):
        """Con 10 días de retraso y 0.5% diario sobre 10000, la multa es 500."""
        proyecto = crear_proyecto(self.empleado, dias_retraso=10,
                                   multa_diaria='0.50', multa_maxima='20.00')
        multa_esperada = Decimal('10000.00') * Decimal('0.50') / Decimal('100') * proyecto.dias_retraso
        self.assertEqual(proyecto.multa_acumulada, multa_esperada)

    def test_multa_no_supera_tope(self):
        """La multa no puede superar el tope máximo (10% = 1000 Bs.)."""
        proyecto = crear_proyecto(self.empleado, dias_retraso=100,
                                   multa_diaria='0.50', multa_maxima='10.00')
        tope = Decimal('10000.00') * Decimal('10.00') / Decimal('100')
        self.assertLessEqual(proyecto.multa_acumulada, tope)
        self.assertEqual(proyecto.estado_multa, 'critico')

    def test_tope_alcanzado_es_critico(self):
        proyecto = crear_proyecto(self.empleado, dias_retraso=200,
                                   multa_diaria='1.00', multa_maxima='5.00')
        self.assertTrue(proyecto.multa_tope_alcanzado)
        self.assertEqual(proyecto.estado_multa, 'critico')


# ===========================================================================
# 4. ContratoEmpleado — monto_diario
# ===========================================================================

class ContratoEmpleadoMontoDiarioTest(TestCase):
    """Verifica el cálculo del monto diario del empleado."""

    def setUp(self):
        self.empleado = crear_empleado(username='instalador', cargo='instalador')

    def test_monto_diario_28_dias(self):
        contrato = ContratoEmpleado.objects.create(
            empleado=self.empleado,
            dias_laborales=28,
            fecha_firma=date.today(),
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            monto_acordado=Decimal('2800.00'),
        )
        self.assertEqual(contrato.monto_diario, Decimal('100.00'))

    def test_monto_diario_30_dias(self):
        contrato = ContratoEmpleado.objects.create(
            empleado=self.empleado,
            dias_laborales=30,
            fecha_firma=date.today(),
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            monto_acordado=Decimal('3000.00'),
        )
        self.assertEqual(contrato.monto_diario, Decimal('100.00'))

    def test_monto_diario_sin_dias_retorna_monto_acordado(self):
        """Cuando dias_laborales=0, monto_diario retorna monto_acordado (guarda del modelo)."""
        contrato = ContratoEmpleado(
            empleado=self.empleado,
            dias_laborales=0,
            monto_acordado=Decimal('2800.00'),
        )
        self.assertEqual(contrato.monto_diario, Decimal('2800.00'))


# ===========================================================================
# 5. InsumoForm — campos básicos
# ===========================================================================

class InsumoFormTest(TestCase):
    """Verifica validación básica del formulario de insumos."""

    def _data(self, **kwargs):
        base = {
            'nombre': 'Camara IP',
            'marca': 'Hikvision',
            'modelo': 'IPC-HDW2831T',
            'categoria': 'camara_ip',
            'unidad_medida': 'unidad',
            'stock_minimo': 5,
        }
        base.update(kwargs)
        return base

    def test_datos_completos_validos(self):
        form = InsumoForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_requerido(self):
        form = InsumoForm(data=self._data(nombre=''))
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_categoria_invalida_rechazada(self):
        form = InsumoForm(data=self._data(categoria='inexistente'))
        self.assertFalse(form.is_valid())
        self.assertIn('categoria', form.errors)


# ===========================================================================
# 6. CompraForm — clean_costo_unitario
# ===========================================================================

class CompraFormCleanCostoTest(TestCase):
    """Verifica que clean_costo_unitario de CompraForm valide el formato decimal."""

    def setUp(self):
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor Test', rubro='camaras_seguridad',
            nit='123456', telefono='70000000', direccion='Av. Test',
        )
        self.insumo = Insumo.objects.create(
            nombre='Camara IP', marca='Hikvision', categoria='camara_ip', unidad_medida='unidad',
        )

    def _data(self, costo):
        return {
            'proveedor': self.proveedor.pk,
            'insumo': self.insumo.pk,
            'cantidad': 1,
            'costo_unitario': costo,
            'fecha': date.today().isoformat(),
            'numero_factura': '',
        }

    def test_costo_valido(self):
        form = CompraForm(data=self._data('350.00'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_entero_valido(self):
        form = CompraForm(data=self._data('350'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_con_coma_invalido(self):
        form = CompraForm(data=self._data('1.200,00'))
        self.assertFalse(form.is_valid())
        self.assertIn('costo_unitario', form.errors)

    def test_costo_cero_invalido(self):
        form = CompraForm(data=self._data('0'))
        self.assertFalse(form.is_valid())
        self.assertIn('costo_unitario', form.errors)

    def test_costo_negativo_invalido(self):
        form = CompraForm(data=self._data('-100'))
        self.assertFalse(form.is_valid())
        self.assertIn('costo_unitario', form.errors)
