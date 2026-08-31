/* ==== Estado del muro de control ====
   Reemplaza el `estado` global de dashboard.js: polling a la API cada 5 s,
   fallback a datos de demostración, avance del sensor simulado cada minuto y
   silenciado (`ack`) de alertas. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { PUERTAS_DEMO, getPuertas } from '../lib/api'
import { TEMP_INTERVALO, avanzarSeries } from '../lib/tempSim'
import type { Puerta } from '../types'

const POLL_MS = 5000
const SILENCIO_MS = 300000 // 5 minutos

export interface EstadoPuertas {
  puertas: Puerta[]
  /**
   * Momento en que llegaron los últimos datos. El modal lo usa para que su
   * cronómetro siga corriendo entre polls en vez de congelarse 5 segundos.
   */
  ultimaActualizacion: number
  /** Silencia la alerta de una puerta, o de todas si no se pasa id. */
  silenciar: (id?: string) => void
}

export function usePuertas(): EstadoPuertas {
  const [puertas, setPuertas] = useState<Puerta[]>([])
  const [ultimaActualizacion, setUltimaActualizacion] = useState(() => Date.now())

  // Los `ack` son estado local: no vienen de la API y no deben perderse en cada
  // poll, así que se guardan aparte y se reaplican sobre los datos que llegan.
  const acks = useRef<Record<string, number>>({})

  const aplicarAcks = useCallback(
    (lista: Puerta[]) => lista.map((e) => ({ ...e, ack: acks.current[e.id] ?? 0 })),
    [],
  )

  /* ---- Polling a la API ---- */
  useEffect(() => {
    let vivo = true

    async function cargar() {
      try {
        const datos = await getPuertas()
        if (!vivo) return
        setPuertas(aplicarAcks(datos))
        setUltimaActualizacion(Date.now())
      } catch (error) {
        // El backend todavía no expone /api/eventos-camaras/ con el formato que
        // espera este muro. Mientras se conecta, se usa un dato de prueba fijo
        // para poder seguir probando la UI y el arranque del modelo YOLO.
        console.warn('No se pudo leer la API de Django, usando datos de prueba:', error)
        if (!vivo) return
        setPuertas((previas) => (previas.length ? previas : aplicarAcks(PUERTAS_DEMO)))
        setUltimaActualizacion(Date.now())
      }
    }

    void cargar()
    const id = setInterval(() => void cargar(), POLL_MS)
    return () => {
      vivo = false
      clearInterval(id)
    }
  }, [aplicarAcks])

  /* ---- Sensor simulado: una lectura nueva por minuto ---- */
  useEffect(() => {
    const id = setInterval(() => setPuertas((previas) => avanzarSeries(previas)), TEMP_INTERVALO)
    return () => clearInterval(id)
  }, [])

  const silenciar = useCallback((id?: string) => {
    const hasta = Date.now() + SILENCIO_MS
    setPuertas((previas) =>
      previas.map((e) => {
        if (id && e.id !== id) return e
        acks.current[e.id] = hasta
        return { ...e, ack: hasta }
      }),
    )
  }, [])

  return { puertas, ultimaActualizacion, silenciar }
}
