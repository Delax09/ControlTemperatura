"""
Publica los eventos de puerta detectados por el modelo en la API de Django.

El worker de analisis detecta; este modulo es el unico que sabe donde se
guardan los datos. Hoy escribe en la tabla de la demo (`/api/eventos/`,
EventoPuerta) porque las tablas nuevas (Door / Event) todavia no tienen sus
migraciones aplicadas. Al aplicarlas, lo que cambia es RUTA_EVENTOS y los
campos de `abrir` y `cerrar`; el worker no se toca.

El flujo es en dos pasos a proposito:

  * apertura -> POST, crea el registro con hora_apertura y sin cierre. Asi la
                puerta abierta ya existe en la base mientras sigue abierta.
  * cierre   -> PATCH, agrega hora_cierre. El modelo calcula la duracion.

Si la API no responde el evento no se pierde: se guarda en
alertas/registro_tiempos_puerta.json, el mismo archivo del flujo anterior, y
queda disponible para cargarlo despues.
"""
import json
import os

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_RESPALDO = os.path.join(BASE_DIR, "alertas", "registro_tiempos_puerta.json")

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/")
RUTA_EVENTOS = "eventos/"
TIMEOUT = 4.0   # el worker no puede quedarse esperando al backend


def _iso(momento):
    """
    ISO 8601 con offset horario.

    Las maquinas de estado usan `datetime.now()` (naive, hora local). Django
    corre con USE_TZ=True: si se manda sin offset interpreta el dato como UTC
    y los eventos quedan corridos las horas del huso.
    """
    if momento.tzinfo is None:
        momento = momento.astimezone()
    return momento.isoformat()


class PublicadorEventos:
    """
    Cliente de escritura de eventos. Tolera que el backend este caido: cada
    fallo se cuenta y se respalda en disco, pero nunca corta el analisis.
    """

    def __init__(self, api_base=API_BASE, timeout=TIMEOUT, respaldar=True, token=None,
                 publicar=True):
        self.api_base = api_base if api_base.endswith("/") else api_base + "/"
        self.timeout = timeout
        self.respaldar = respaldar
        # publicar=False deja el analisis midiendo pero sin escribir en la base
        # (util para probar el modelo sin ensuciar los datos).
        self.publicar = publicar
        self.headers = {"Authorization": f"Token {token}"} if token else {}

        self.registrados = 0    # eventos cerrados y confirmados por la API
        self.fallidos = 0       # eventos que solo quedaron en el respaldo
        # id que devolvio la API por cada zona con apertura en curso
        self._abiertos = {}

    # --- API ---
    @property
    def url_eventos(self):
        return f"{self.api_base}{RUTA_EVENTOS}"

    def abrir(self, zona, hora_apertura, confianza):
        """Crea el registro de la apertura. Guarda el id para el cierre."""
        if not self.publicar:
            self._abiertos[zona] = None
            return

        payload = {
            "evento": "puerta_abierta",
            "hora_apertura": _iso(hora_apertura),
            "confianza_promedio": round(float(confianza), 2),
        }
        try:
            respuesta = requests.post(
                self.url_eventos, json=payload, headers=self.headers, timeout=self.timeout
            )
            respuesta.raise_for_status()
            self._abiertos[zona] = respuesta.json().get("id")
            print(f"      -> apertura registrada en la API (id {self._abiertos[zona]})")
        except Exception as error:
            self._abiertos[zona] = None
            print(f"      -> [AVISO] no se pudo registrar la apertura: {_motivo(error)}")

    def cerrar(self, zona, hora_apertura, hora_cierre, duracion, confianza_promedio):
        """
        Completa el registro con la hora de cierre.

        Si la apertura nunca llego a la API (backend caido en ese momento) se
        intenta crear el evento completo de una vez, y si eso tambien falla se
        respalda en disco.
        """
        evento_id = self._abiertos.pop(zona, None)
        promedio = round(float(confianza_promedio), 2)
        respaldo = {
            "evento": "puerta_abierta",
            "puerta": zona,
            "hora_apertura": _iso(hora_apertura),
            "hora_cierre": _iso(hora_cierre),
            "duracion_segundos": round(duracion, 2),
            "confianza_promedio": promedio,
        }

        if not self.publicar:
            self._respaldar(respaldo)
            return

        try:
            if evento_id:
                respuesta = requests.patch(
                    f"{self.url_eventos}{evento_id}/",
                    json={"hora_cierre": _iso(hora_cierre), "confianza_promedio": promedio},
                    headers=self.headers,
                    timeout=self.timeout,
                )
            else:
                respuesta = requests.post(
                    self.url_eventos,
                    json={
                        "evento": "puerta_abierta",
                        "hora_apertura": _iso(hora_apertura),
                        "hora_cierre": _iso(hora_cierre),
                        "confianza_promedio": promedio,
                    },
                    headers=self.headers,
                    timeout=self.timeout,
                )
            respuesta.raise_for_status()
            self.registrados += 1
            print(f"      -> cierre registrado en la API ({duracion:.1f}s)")
            return
        except Exception as error:
            print(f"      -> [AVISO] no se pudo registrar el cierre: {_motivo(error)}")

        self.fallidos += 1
        if self.respaldar:
            self._respaldar(respaldo)

    # --- Respaldo local ---
    def _respaldar(self, evento):
        """Agrega el evento al JSON de respaldo, sin perder lo que ya estaba."""
        try:
            os.makedirs(os.path.dirname(RUTA_RESPALDO), exist_ok=True)
            registros = []
            if os.path.exists(RUTA_RESPALDO):
                with open(RUTA_RESPALDO, "r", encoding="utf-8") as archivo:
                    contenido = json.load(archivo)
                    registros = contenido if isinstance(contenido, list) else []
            registros.append(evento)
            with open(RUTA_RESPALDO, "w", encoding="utf-8") as archivo:
                json.dump(registros, archivo, indent=4, ensure_ascii=False)
            print("      -> evento guardado en alertas/registro_tiempos_puerta.json")
        except Exception as error:
            print(f"      -> [ERROR] tampoco se pudo respaldar en disco: {error}")

    def disponible(self):
        """True si la API responde. Se usa al arrancar, para avisar temprano."""
        try:
            requests.get(self.url_eventos, headers=self.headers, timeout=self.timeout).raise_for_status()
            return True
        except Exception:
            return False


def _motivo(error):
    """Mensaje corto del error, con el detalle de validacion si la API lo dio."""
    respuesta = getattr(error, "response", None)
    if respuesta is not None:
        return f"HTTP {respuesta.status_code} {respuesta.text[:200]}"
    return f"{type(error).__name__}: {error}"
