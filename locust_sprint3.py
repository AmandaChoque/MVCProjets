"""
SPRINT 3 - MÓDULO DE PERSONAL
==============================
Ejecutar con:
    locust -f locust_sprint3.py --host=http://localhost:8000

Luego abrir: http://localhost:8089
Configurar: 250 usuarios, ramp-up 10 segundos
"""

from locust import HttpUser, task, between
from bs4 import BeautifulSoup


class UsuarioPersonal(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Login al inicio de cada usuario simulado"""
        response = self.client.get("/signin/")
        soup = BeautifulSoup(response.text, "html.parser")
        csrf = soup.find("input", {"name": "csrfmiddlewaretoken"})
        csrf_token = csrf["value"] if csrf else ""

        self.client.post("/signin/", data={
            "username": "admin",       # <-- cambia por tu usuario
            "password": "admin123",    # <-- cambia por tu contraseña
            "csrfmiddlewaretoken": csrf_token,
        }, headers={"Referer": "http://localhost:8000/signin/"})

    @task(3)
    def listar_empleados(self):
        self.client.get("/empleados/", name="Lista de empleados")

    @task(2)
    def listar_pagos_empleados(self):
        self.client.get("/pagos-empleados/", name="Lista de pagos empleados")

    @task(2)
    def reporte_empleados(self):
        self.client.get("/empleados/reporte/", name="Reporte de empleados")

    @task(1)
    def mi_trabajo(self):
        self.client.get("/mi-trabajo/", name="Dashboard Mi trabajo")

    @task(1)
    def mis_cobros(self):
        self.client.get("/mis-cobros/", name="Mis cobros")
