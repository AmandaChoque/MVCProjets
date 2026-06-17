#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

# Crear superusuario inicial si no existe
python manage.py create_initial_superuser