"""
SPRINT 1 - MÓDULO DE PROYECTOS
================================
Ejecutar con:
    locust -f locust_sprint1.py --host=http://localhost:8000

Luego abrir: http://localhost:8089
Configurar: 250 usuarios, ramp-up 10 segundos
"""

from locust import HttpUser, task, between
from bs4 import BeautifulSoup


class UsuarioProyectos(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Login al inicio de cada usuario simulado"""  
        # Obtener token CSRF de la página de login
        response = self.client.get("/signin/")
        soup = BeautifulSoup(response.text, "html.parser")
        csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})
        csrf_token = csrf["value"] if csrf else ""

        # Hacer login
        self.client.post("/signin/", data={
            "username": "admin",       # <-- cambia por tu usuario
            "password": "admin123",    # <-- cambia por tu contraseña
            "csrfmiddlewaretoken": csrf_token,
        }, headers={"Referer": "http://localhost:8000/signin/"})

    @task(3)
    def listar_proyectos(self):
        self.client.get("/proyectos/", name="Lista de proyectos")

    @task(3)
    def listar_clientes(self):
        self.client.get("/clientes/", name="Lista de clientes")

    @task(2)
    def listar_pagos(self):
        self.client.get("/pagos/", name="Lista de pagos")

    @task(1)
    def dashboard(self):
        self.client.get("/dashboard/", name="Dashboard")
