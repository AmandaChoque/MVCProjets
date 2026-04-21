"""
SPRINT 2 - MÓDULO DE INVENTARIO Y COMPRAS
==========================================
Ejecutar con:
    locust -f locust_sprint2.py --host=http://localhost:8000

Luego abrir: http://localhost:8089
Configurar: 250 usuarios, ramp-up 10 segundos
"""

from locust import HttpUser, task, between
from bs4 import BeautifulSoup


class UsuarioInventario(HttpUser):
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
    def listar_insumos(self):
        self.client.get("/insumos/", name="Lista de insumos")

    @task(3)
    def listar_proveedores(self):
        self.client.get("/proveedores/", name="Lista de proveedores")

    @task(2)
    def listar_compras(self):
        self.client.get("/compras/", name="Lista de compras")

    @task(1)
    def reporte_inventario(self):
        self.client.get("/inventario/reporte/", name="Reporte de inventario")
