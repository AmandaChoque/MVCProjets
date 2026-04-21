from decimal import Decimal
from datetime import date

from django.test import TestCase

from .models import Cliente, Proyecto, Pago
from .form import PaymentForm
from empleados.models import Empleado
from inventario.forms import InsumoForm


# ---------------------------------------------------------------------------
# Helpers reutilizables
# ---------------------------------------------------------------------------

def crear_empleado(username='testuser'):
    return Empleado.objects.create_user(
        username=username,
        password='pass1234',
        nombre='Test',
        apellido_paterno='User',
        carnet_identidad='1234560',
        cargo='administrador',
    )


def crear_cliente():
    return Cliente.objects.create(
        nombre='Ana',
        apellido_paterno='Lopez',
        nit_ci='1234567',
        tipo_contratante='personal',
        telefono='70000001',
        cargo='Gerente',
        direccion='Av. Siempre Viva',
    )


def crear_proyecto(empleado, monto_total='10000.00'):
    return Proyecto.objects.create(
        codigo='PRY-001',
        nombre='Instalacion SOBOTEC Test',
        estado_proyecto='pendiente',
        tipo_proyecto='instalacion_nueva',
        estado_pago='no_pagado',
        monto_total=Decimal(monto_total),
        creado_por=empleado,
        cliente=crear_cliente(),
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

    # --- Casos validos ---

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
        """El form debe convertir el string a Decimal."""
        form = PaymentForm(data=self._data('3500.75'))
        form.is_valid()
        self.assertEqual(form.cleaned_data['monto'], Decimal('3500.75'))

    # --- Casos invalidos ---

    def test_monto_con_coma_invalido(self):
        """Bolivia usa punto como separador decimal, no coma."""
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
# 2. Proyecto._sync_estado_pago — logica de negocio y senal post_save
# ===========================================================================

class UpdatePaymentStatusTest(TestCase):
    """Verifica que el estado_pago del proyecto se actualice correctamente."""

    def setUp(self):
        self.empleado = crear_empleado()
        self.proyecto = crear_proyecto(self.empleado, monto_total='10000.00')

    def _pago(self, monto):
        return Pago.objects.create(
            monto=Decimal(monto),
            fecha=date.today(),
            tipo_pago='efectivo',
            proyecto=self.proyecto,
            activo=True,
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
        """Pagos con activo=False no deben sumar al total pagado."""
        pago = self._pago('10000.00')
        pago.activo = False
        pago.save()
        self.proyecto._sync_estado_pago()
        self.proyecto.refresh_from_db()
        self.assertNotEqual(self.proyecto.estado_pago, 'pagado')

    def test_senal_post_save_actualiza_proyecto_automaticamente(self):
        """La senal post_save de Pago debe actualizar estado_pago sin llamar _sync manualmente."""
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'no_pagado')

        Pago.objects.create(
            monto=Decimal('10000.00'),
            fecha=date.today(),
            tipo_pago='efectivo',
            proyecto=self.proyecto,
            activo=True,
        )

        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.estado_pago, 'pagado')


# ===========================================================================
# 3. InsumoForm — clean_costo_unitario
# ===========================================================================

class InsumoFormCleanCostoTest(TestCase):
    """Verifica la validacion del costo unitario de insumos."""

    def _data(self, costo):
        return {
            'nombre': 'Camara IP',
            'marca': 'Hikvision',
            'modelo': '',
            'categoria': 'camara_ip',
            'costo_unitario': costo,
            'stock_minimo': 5,
        }

    def test_costo_valido(self):
        form = InsumoForm(data=self._data('350.00'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_entero_valido(self):
        form = InsumoForm(data=self._data('350'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_con_coma_invalido(self):
        form = InsumoForm(data=self._data('1.200,00'))
        self.assertFalse(form.is_valid())
        self.assertIn('costo_unitario', form.errors)

    def test_costo_cero_valido(self):
        """Costo cero es permitido — el precio referencial es opcional en InsumoForm."""
        form = InsumoForm(data=self._data('0'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_costo_vacio_valido(self):
        """Costo vacío es permitido — se actualiza automáticamente desde las compras."""
        form = InsumoForm(data=self._data(''))
        self.assertTrue(form.is_valid(), form.errors)
