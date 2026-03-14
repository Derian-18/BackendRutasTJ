from django.test import TestCase
import json
from django.urls import reverse

from apps.principal.models import Conexion, Parada, Ruta
from apps.rutas.views import dijkstra_con_transbordos


class DijkstraConTransbordosTests(TestCase):
    def setUp(self):
        self.p1 = Parada.objects.create(nombre="P1", latitud=32.50, longitud=-117.00)
        self.p2 = Parada.objects.create(nombre="P2", latitud=32.51, longitud=-117.00)
        self.p3 = Parada.objects.create(nombre="P3", latitud=32.52, longitud=-117.00)
        self.p4 = Parada.objects.create(nombre="P4", latitud=32.53, longitud=-117.00)

        self.ruta_a = Ruta.objects.create(nombre="Ruta A")
        self.ruta_b = Ruta.objects.create(nombre="Ruta B")

    def test_prioriza_menos_transbordos_antes_que_distancia(self):
        # Camino directo por Ruta A (sin transbordo), pero más largo.
        Conexion.objects.create(origen=self.p1, destino=self.p2, distancia=1000, bidireccional=True, ruta=self.ruta_a)
        Conexion.objects.create(origen=self.p2, destino=self.p4, distancia=1000, bidireccional=True, ruta=self.ruta_a)

        # Camino más corto en distancia total, pero con transbordo A -> B.
        Conexion.objects.create(origen=self.p1, destino=self.p3, distancia=300, bidireccional=True, ruta=self.ruta_a)
        Conexion.objects.create(origen=self.p3, destino=self.p4, distancia=300, bidireccional=True, ruta=self.ruta_b)

        camino = dijkstra_con_transbordos(self.p1.id, self.p4.id)

        rutas_por_paso = [ruta for _, ruta in camino if ruta is not None]
        self.assertTrue(rutas_por_paso)
        self.assertEqual(set(rutas_por_paso), {self.ruta_a.id})

    def test_devuelve_vacio_si_no_hay_ruta(self):
        camino = dijkstra_con_transbordos(self.p1.id, self.p4.id)
        self.assertEqual(camino, [])


class CalcularRutaViewTests(TestCase):
    def test_indica_cuando_la_ruta_es_directa(self):
        p1 = Parada.objects.create(nombre="Origen", latitud=32.5000, longitud=-117.0000)
        p2 = Parada.objects.create(nombre="Intermedia", latitud=32.5005, longitud=-117.0000)
        p3 = Parada.objects.create(nombre="Destino", latitud=32.5010, longitud=-117.0000)
        ruta = Ruta.objects.create(nombre="Ruta Directa")

        Conexion.objects.create(origen=p1, destino=p2, distancia=100, bidireccional=True, ruta=ruta)
        Conexion.objects.create(origen=p2, destino=p3, distancia=100, bidireccional=True, ruta=ruta)

        response = self.client.post(
            reverse("calcular_ruta"),
            data=json.dumps({
                "latA": p1.latitud,
                "lonA": p1.longitud,
                "latB": p3.latitud,
                "lonB": p3.longitud,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["requiere_transbordo"])
        self.assertEqual(data["total_transbordos"], 0)


    def test_evita_transbordo_si_hay_ruta_directa_desde_otra_parada_cercana(self):
        # Dos paradas cerca del origen: una obliga transbordo y otra tiene ruta directa.
        p_origen_transbordo = Parada.objects.create(nombre="Origen Transbordo", latitud=32.50000, longitud=-117.00000)
        p_origen_directo = Parada.objects.create(nombre="Origen Directo", latitud=32.50015, longitud=-117.00000)
        p_intermedia = Parada.objects.create(nombre="Intermedia", latitud=32.50100, longitud=-117.00000)
        p_destino = Parada.objects.create(nombre="Destino", latitud=32.50200, longitud=-117.00000)

        ruta_a = Ruta.objects.create(nombre="Ruta A")
        ruta_b = Ruta.objects.create(nombre="Ruta B")
        ruta_directa = Ruta.objects.create(nombre="Ruta Directa")

        # Camino con transbordo: A -> B
        Conexion.objects.create(origen=p_origen_transbordo, destino=p_intermedia, distancia=100, bidireccional=True, ruta=ruta_a)
        Conexion.objects.create(origen=p_intermedia, destino=p_destino, distancia=100, bidireccional=True, ruta=ruta_b)

        # Camino directo un poco más lejos del clic inicial, pero sin transbordo.
        Conexion.objects.create(origen=p_origen_directo, destino=p_destino, distancia=250, bidireccional=True, ruta=ruta_directa)

        response = self.client.post(
            reverse("calcular_ruta"),
            data=json.dumps({
                "latA": 32.50002,
                "lonA": -117.00000,
                "latB": p_destino.latitud,
                "lonB": p_destino.longitud,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["requiere_transbordo"])
        self.assertEqual(data["total_transbordos"], 0)

        rutas_tomadas = [paso["ruta"] for paso in data["ruta_optima"] if paso["tipo"] == "transbordo"]
        self.assertEqual(rutas_tomadas, ["Ruta Directa"])
