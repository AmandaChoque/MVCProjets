import re
from decimal import Decimal
from django.core.exceptions import ValidationError

# ── Shared form utilities ──────────────────────────────────────────────────────

DECIMAL_REGEX = r'\d+(\.\d{1,2})?'
VALID_PER_PAGE = (10, 20, 50, 100)
_ALLOWED_DOC_EXT = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp')


def parse_decimal(valor):
    """Parse a decimal string. Raises ValidationError on bad format."""
    valor_str = str(valor).strip()
    if not re.fullmatch(DECIMAL_REGEX, valor_str):
        raise ValidationError('Formato inválido. Use punto como separador decimal (ej: 5000 o 5000.50).')
    return Decimal(valor_str)


def validate_phone(value, min_len=7, max_len=None, required=True):
    """Strip, validate digits and length. Returns cleaned phone string."""
    phone = str(value).strip().replace(' ', '').replace('-', '')
    if not phone:
        if required:
            raise ValidationError('El teléfono es obligatorio.')
        return phone
    if not phone.isdigit():
        raise ValidationError('El teléfono debe contener solo números.')
    if len(phone) < min_len:
        raise ValidationError(f'El teléfono debe tener al menos {min_len} dígitos.')
    if max_len and len(phone) > max_len:
        raise ValidationError(f'El teléfono no puede superar los {max_len} dígitos.')
    return phone


def validate_numeric_id(value, min_len=6, required=False):
    """Strip spaces, validate all-digits and minimum length. Returns cleaned string."""
    digits = str(value).strip().replace(' ', '')
    if not digits:
        if required:
            raise ValidationError('Este campo es obligatorio.')
        return digits
    if not digits.isdigit():
        raise ValidationError('Debe contener solo números.')
    if len(digits) < min_len:
        raise ValidationError(f'Debe tener al menos {min_len} dígitos.')
    return digits


def validate_document_ext(doc):
    """Accept PDF or common image formats. Returns doc unchanged."""
    if doc and hasattr(doc, 'name'):
        if not doc.name.lower().endswith(_ALLOWED_DOC_EXT):
            raise ValidationError('Solo se permiten archivos PDF o imágenes (JPG, PNG, GIF, WEBP).')
    return doc


def parse_pagination(request, default_per_page=10):
    """Extract and sanitize page/per_page from request.GET. Returns (page, per_page)."""
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.GET.get('per_page', default_per_page))
        if per_page not in VALID_PER_PAGE:
            per_page = default_per_page
    except (ValueError, TypeError):
        per_page = default_per_page
    return page, per_page


# ── Password validators ────────────────────────────────────────────────────────

class UppercaseValidator:
    """La contraseña debe contener al menos una letra mayúscula."""

    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return 'La contraseña debe contener al menos una letra mayúscula (A-Z).'


class LowercaseValidator:
    """La contraseña debe contener al menos una letra minúscula."""

    def validate(self, password, user=None):
        if not re.search(r'[a-z]', password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return 'La contraseña debe contener al menos una letra minúscula (a-z).'


class NumberValidator:
    """La contraseña debe contener al menos un número."""

    def validate(self, password, user=None):
        if not re.search(r'[0-9]', password):
            raise ValidationError(self.get_help_text())

    def get_help_text(self):
        return 'La contraseña debe contener al menos un número (0-9).'
