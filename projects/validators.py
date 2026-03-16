import re
from django.core.exceptions import ValidationError


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
