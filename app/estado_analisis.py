"""
Protocolo de estado entre el worker de analisis y el backend.

El worker (app/analisis_en_vivo.py) corre como proceso aparte de Django, asi
que no comparten memoria: se hablan por archivos en alertas/analisis/.

  <puerta>.json  -> lo escribe el worker cada SEGUNDOS_LATIDO: pid, estado de
                    cada zona, eventos registrados y la marca de tiempo del
                    ultimo latido. Django solo lo lee.
  <puerta>.stop  -> lo crea Django al pulsar "Detener". El worker lo ve, cierra
                    la apertura en curso y sale limpio. Solo el worker lo borra.

Este modulo se mantiene sin cv2, ultralytics ni Django a proposito: lo importan
los dos lados, y el backend no puede pagar el costo de cargar el modelo.

Por que un archivo y no una variable en memoria de Django: el runserver se
reinicia solo al guardar codigo, y con eso se perderia el registro de que hay
un analisis corriendo. El archivo sobrevive al reinicio.
"""
import json
import os
import re
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ESTADO = os.path.join(BASE_DIR, "alertas", "analisis")

SEGUNDOS_LATIDO = 2.0       # cada cuanto reescribe el worker su estado
# Un worker cuyo latido sea mas viejo que esto se considera muerto. Tiene que
# ser bastante mayor que SEGUNDOS_LATIDO: un frame de 1080p en CPU puede tardar
# medio segundo y el worker no escribe mientras infiere.
SEGUNDOS_SIN_LATIDO = 15.0
# Mientras arranca, un worker no late: importar torch, cargar los pesos y
# negociar el RTSP se lleva facil medio minuto en CPU. Durante esa ventana el
# estado "iniciando" se considera vivo aunque el latido este viejo, para que
# nadie levante un segundo worker sobre la misma camara.
SEGUNDOS_ARRANQUE = 120.0

# Reintentos al leer el estado, para no confundir una colision con el os.replace
# del worker con la ausencia de analisis (ver leer_estado).
INTENTOS_LECTURA = 4
ESPERA_REINTENTO = 0.05

ESTADOS_VIVOS = ("iniciando", "corriendo")


def slug(puerta_id):
    """Nombre de archivo seguro para el id de puerta que llega del muro."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(puerta_id)).strip("_") or "puerta"


def ruta_estado(puerta_id):
    return os.path.join(DIR_ESTADO, f"{slug(puerta_id)}.json")


def ruta_detener(puerta_id):
    return os.path.join(DIR_ESTADO, f"{slug(puerta_id)}.stop")


def leer_estado(puerta_id):
    """
    El ultimo estado que dejo el worker, o None si no hay.

    Se reintenta porque en Windows el os.replace con que el worker publica su
    estado choca de vez en cuando con una lectura simultanea y la abre con
    PermissionError (una de cada mil, medido). Sin reintentar, ese choque se
    confunde con "no hay ningun analisis": basta que caiga sobre el request de
    "Detener" para que el muro conteste que no hay nada corriendo.

    Un JSON invalido tambien devuelve None: si el archivo quedo a medias por un
    corte de energia no vale la pena romper la vista por eso.
    """
    ruta = ruta_estado(puerta_id)
    for intento in range(INTENTOS_LECTURA):
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                return json.load(archivo)
        except FileNotFoundError:
            return None                      # no hay analisis: respuesta definitiva
        except (OSError, json.JSONDecodeError):
            if intento == INTENTOS_LECTURA - 1:
                return None
            time.sleep(ESPERA_REINTENTO)     # publicacion en curso: se reintenta
    return None


def esta_vivo(estado):
    """
    True si el estado leido corresponde a un worker que sigue en pie.

    Un worker "corriendo" tiene que estar latiendo; uno "iniciando" recien se
    lanzo y todavia no puede latir, asi que se le da SEGUNDOS_ARRANQUE. Si
    murio al arrancar (falta el modelo, camara inalcanzable) escribe "error" y
    deja de contar como vivo de inmediato; el plazo largo solo cubre el caso de
    que se caiga sin poder escribir nada.
    """
    if not estado or estado.get("estado") not in ESTADOS_VIVOS:
        return False
    try:
        latido = datetime.fromisoformat(estado["ultimo_latido"])
    except (KeyError, TypeError, ValueError):
        return False

    plazo = SEGUNDOS_SIN_LATIDO if estado["estado"] == "corriendo" else SEGUNDOS_ARRANQUE
    return (datetime.now() - latido).total_seconds() <= plazo


def reservar(puerta_id, origen="", en_vivo=False, mensaje="Lanzando el worker de analisis"):
    """
    Marca la puerta como "iniciando" antes de lanzar el proceso.

    Lo llama el backend justo antes del Popen. Sin esto hay una ventana de
    varios segundos —lo que el worker tarda en importar sus dependencias y
    escribir su primer estado— en la que una segunda pulsacion del boton
    levantaria otro worker sobre la misma camara y cada evento se guardaria dos
    veces. El worker sobreescribe este archivo en cuanto arranca.
    """
    ArchivoEstado(puerta_id, origen, en_vivo).escribir("iniciando", [], mensaje=mensaje)


def liberar(puerta_id):
    """Borra el estado de la puerta. Se usa si el worker no llego a lanzarse."""
    try:
        os.remove(ruta_estado(puerta_id))
    except OSError:
        pass


def analisis_vivos():
    """
    {puerta: estado} de todos los analisis con latido reciente.

    Lo usa el backend para no arrancar dos workers sobre la misma camara: hoy
    hay un solo origen de video, y dos procesos leyendolo duplicarian cada
    evento en la base.
    """
    vivos = {}
    if not os.path.isdir(DIR_ESTADO):
        return vivos

    for nombre in os.listdir(DIR_ESTADO):
        if not nombre.endswith(".json"):
            continue
        estado = leer_estado(nombre[:-len(".json")])
        if esta_vivo(estado):
            vivos[estado.get("puerta", nombre[:-len(".json")])] = estado
    return vivos


def pedir_detencion(puerta_id):
    """Deja la senal de detencion. El worker la borra al salir."""
    os.makedirs(DIR_ESTADO, exist_ok=True)
    ruta = ruta_detener(puerta_id)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(datetime.now().isoformat(timespec="seconds"))
    return ruta


def referencia_detencion(puerta_id):
    """
    Instante a partir del cual una senal de detencion pertenece a esta sesion.

    El backend escribe la reserva justo antes de lanzar el worker, asi que todo
    .stop mas nuevo que ese archivo lo pidio el operador para esta sesion, y
    todo .stop mas viejo es basura de una sesion anterior que murio sin
    consumirlo. Sin esta referencia el worker no puede distinguirlos, y si
    borrara la senal al arrancar se perderia el "Detener" pulsado mientras
    todavia cargaba el modelo.

    En un arranque manual por consola no hay reserva: solo cuentan las senales
    posteriores a este momento.
    """
    try:
        return os.path.getmtime(ruta_estado(puerta_id))
    except OSError:
        return time.time()


def detencion_pedida(puerta_id, desde=None):
    """True si hay una senal de detencion vigente (ver referencia_detencion)."""
    try:
        pedida_en = os.path.getmtime(ruta_detener(puerta_id))
    except OSError:
        return False
    return desde is None or pedida_en >= desde


def limpiar_detencion(puerta_id):
    """Borra la senal, si existe. Sin ella un worker nuevo saldria de inmediato."""
    try:
        os.remove(ruta_detener(puerta_id))
    except OSError:
        pass


class ArchivoEstado:
    """
    Escribe el estado del worker para que el backend lo lea.

    Se escribe a un .tmp y despues se reemplaza: Django puede leer en cualquier
    momento y no debe encontrarse un JSON a medio escribir.
    """

    def __init__(self, puerta_id, origen, en_vivo, pid=None):
        self.ruta = ruta_estado(puerta_id)
        self.base = {
            "puerta": str(puerta_id),
            # None mientras es solo una reserva: el pid real lo escribe el
            # worker cuando toma el relevo.
            "pid": pid,
            "origen": origen,       # ya enmascarado: no debe filtrar la clave RTSP
            "en_vivo": bool(en_vivo),
            "iniciado": datetime.now().isoformat(timespec="seconds"),
        }
        os.makedirs(DIR_ESTADO, exist_ok=True)

    def escribir(self, estado, zonas, registrados=0, sin_enviar=0, fps=0.0,
                 reconexiones=0, mensaje="", ventana=False):
        datos = dict(self.base)
        datos.update({
            "estado": estado,
            "mensaje": mensaje,
            # Si el visor esta abierto ahora mismo. No es dato de la sesion: el
            # operador puede cerrarlo sin detener el analisis.
            "ventana": bool(ventana),
            "ultimo_latido": datetime.now().isoformat(timespec="seconds"),
            "fps_analisis": round(fps, 1),
            "eventos_registrados": registrados,
            "eventos_sin_enviar": sin_enviar,
            "reconexiones": reconexiones,
            "zonas": zonas,
        })

        temporal = f"{self.ruta}.tmp"
        try:
            with open(temporal, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, indent=2, ensure_ascii=False)
            os.replace(temporal, self.ruta)
        except OSError as error:
            print(f"[AVISO] no se pudo escribir el estado del analisis: {error}")
