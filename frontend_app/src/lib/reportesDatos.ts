/* ==== Datos simulados del reporte general ====
   TEMPORAL, igual que tempSim.ts: el backend todavía no tiene identidad de
   puerta en EventoPuerta, así que no existe de dónde leer un consolidado por
   cámara. Este módulo genera uno plausible para diseñar la vista.

   Dos decisiones importantes:

   1. La aleatoriedad es DETERMINISTA (PRNG sembrado por puerta + hora). Un
      ranking que se reordena en cada repintado no sirve para nada. Los mismos
      datos salen siempre, y solo cambian al cambiar de hora.

   2. La deriva de temperatura no se sortea: se deriva de los minutos abiertos
      con la misma saturación exponencial que usa tempSim.ts, así que una
      puerta más tiempo abierta siempre calienta más. Ranking y temperatura son
      coherentes entre sí. */

import type { FilaReporte, HoraReporte, Reporte, TipoRecinto } from '../types'

interface PuertaFlota {
  id: string
  nombre: string
  zona: string
  setPoint: number
  tipo: TipoRecinto
  /** Intensidad de uso relativa: multiplica las aperturas por hora. */
  intensidad: number
}

export const FLOTA: PuertaFlota[] = [
  { id: 'PSP-01', nombre: 'ANDÉN PSP 1', zona: 'Andén despacho · rápida 3 m', setPoint: -0.5, tipo: 'anden', intensidad: 1.0 },
  { id: 'PSP-02', nombre: 'ANDÉN PSP 2', zona: 'Andén recepción · rápida 3 m', setPoint: -0.5, tipo: 'anden', intensidad: 0.92 },
  { id: 'DES-01', nombre: 'DESPACHO SUR', zona: 'Andén sur seccional', setPoint: 2.0, tipo: 'anden', intensidad: 0.78 },
  { id: 'MP-02', nombre: 'MATERIA PRIMA 2', zona: 'Recepción materia prima', setPoint: 0.0, tipo: 'mp', intensidad: 0.71 },
  { id: 'PTT-01', nombre: 'PASILLO PTT 1', zona: 'Pasillo pre-túnel', setPoint: 2.0, tipo: 'pasillo', intensidad: 0.55 },
  { id: 'CF-03', nombre: 'CÁMARA FRÍO 3', zona: 'PT congelado', setPoint: -18.0, tipo: 'congelado', intensidad: 0.38 },
  { id: 'CF-04', nombre: 'CÁMARA FRÍO 4', zona: 'PT congelado', setPoint: -18.0, tipo: 'congelado', intensidad: 0.3 },
  { id: 'TC-01', nombre: 'TÚNEL CONG. 1', zona: 'Túnel de congelado', setPoint: -28.0, tipo: 'tunel', intensidad: 0.16 },
]

const AMBIENTE_REPORTE = 12 // °C del pasillo/andén que entra al abrir
const K_DERIVA = 0.05 // saturación por minuto abierto

/** PRNG determinista (mulberry32) sembrado con un hash de la clave. */
function rngDe(clave: string): () => number {
  let h = 2166136261
  for (let i = 0; i < clave.length; i++) h = Math.imul(h ^ clave.charCodeAt(i), 16777619)
  let s = h >>> 0
  return function () {
    s = (s + 0x6d2b79f5) | 0
    let t = Math.imul(s ^ (s >>> 15), 1 | s)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Índice absoluto de hora: estable dentro de la misma hora del reloj. */
const horaAbsoluta = (ts: number) => Math.floor(ts / 3600000)

/** Una hora de actividad de una puerta. */
function horaDe(puerta: PuertaFlota, hAbs: number): HoraReporte {
  const r = rngDe(`${puerta.id}-${hAbs}`)

  // La actividad baja de noche (turno reducido).
  const hora = ((hAbs % 24) + 24) % 24
  const factorTurno = hora >= 7 && hora < 23 ? 1 : 0.28

  const aperturas = Math.round(r() * 9 * puerta.intensidad * factorTurno)
  // Minutos abiertos: cada apertura aporta entre 0,4 y 5 minutos.
  let minutos = 0
  for (let i = 0; i < aperturas; i++) minutos += 0.4 + r() * 4.6
  minutos = Math.min(60, minutos)

  // Deriva térmica saturante: coherente con el modelo de tempSim.ts.
  const techo = AMBIENTE_REPORTE - puerta.setPoint
  const deriva = techo * (1 - Math.exp(-K_DERIVA * minutos))

  return {
    hAbs,
    hora,
    aperturas,
    minutos: +minutos.toFixed(1),
    deriva: +Math.max(0, deriva).toFixed(1),
    tempMax: +(puerta.setPoint + deriva).toFixed(1),
  }
}

/** Consolidado de una puerta en una ventana de N horas (la más reciente al final). */
function resumenPuerta(puerta: PuertaFlota, horas: number, ahora: number): FilaReporte {
  const hAhora = horaAbsoluta(ahora)
  const serie: HoraReporte[] = []
  for (let k = horas - 1; k >= 0; k--) serie.push(horaDe(puerta, hAhora - k))

  const minutos = serie.reduce((a, h) => a + h.minutos, 0)
  const aperturas = serie.reduce((a, h) => a + h.aperturas, 0)
  const derivaMax = Math.max(...serie.map((h) => h.deriva))
  const horasFuera = serie.filter((h) => h.deriva > 1.2).length

  return {
    id: puerta.id,
    nombre: puerta.nombre,
    zona: puerta.zona,
    setPoint: puerta.setPoint,
    tipo: puerta.tipo,
    serie,
    minutos: +minutos.toFixed(1),
    aperturas,
    derivaMax: +derivaMax.toFixed(1),
    tempMax: +(puerta.setPoint + derivaMax).toFixed(1),
    horasFuera,
    // Minutos promedio por apertura: indica si el problema es frecuencia o duración.
    minPorApertura: aperturas ? +(minutos / aperturas).toFixed(1) : 0,
  }
}

/** Reporte completo, ordenado por tiempo abierto (el ranking pedido). */
export function generarReporte(horas: number): Reporte {
  const ahora = Date.now()
  const filas = FLOTA.map((p) => resumenPuerta(p, horas, ahora)).sort((a, b) => b.minutos - a.minutos)
  return {
    horas,
    generado: new Date(ahora),
    filas,
    totalMinutos: +filas.reduce((a, f) => a + f.minutos, 0).toFixed(1),
    totalAperturas: filas.reduce((a, f) => a + f.aperturas, 0),
    peorDeriva: filas.reduce((m, f) => (f.derivaMax > m.derivaMax ? f : m), filas[0]),
    puertasFuera: filas.filter((f) => f.horasFuera > 0).length,
  }
}
