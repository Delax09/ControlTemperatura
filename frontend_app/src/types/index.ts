/* ==== Contratos de datos del muro de control ==== */

/** Nivel de severidad de una puerta, derivado del tiempo abierta. */
export type Nivel = 'ok' | 'open' | 'warn' | 'serious' | 'crit'

/** Tipo de recinto, solo se usa para el color del placeholder de cámara. */
export type TipoRecinto = 'anden' | 'pasillo' | 'congelado' | 'tunel' | 'mp' | 'sala'

/**
 * Una puerta tal como la entrega (o la entregará) la API de Django.
 * `ack` es estado local del frontend: hasta cuándo está silenciada la alerta.
 */
export interface Puerta {
  id: string
  nombre: string
  zona: string
  cam?: string
  tipo: TipoRecinto
  temp_objetivo: number
  temp_actual: number
  abierta: boolean
  segundos_abierta: number
  aperturas_hoy: number
  minutos_hoy: number
  offline: boolean
  historial_aperturas: number[]
  /** Timestamp hasta el que la alerta está silenciada. Solo frontend. */
  ack?: number
}

/** Una muestra de la serie de temperatura. */
export interface Muestra {
  t: Date
  v: number
}

/** Filtro del muro de control. */
export type Filtro = 'all' | 'open' | 'alert'

/* ---- Reporte general ---- */

/** Actividad de una puerta durante una hora del reloj. */
export interface HoraReporte {
  hAbs: number
  hora: number
  aperturas: number
  minutos: number
  deriva: number
  tempMax: number
}

/** Consolidado de una puerta en la ventana del reporte. */
export interface FilaReporte {
  id: string
  nombre: string
  zona: string
  setPoint: number
  tipo: TipoRecinto
  serie: HoraReporte[]
  minutos: number
  aperturas: number
  derivaMax: number
  tempMax: number
  horasFuera: number
  minPorApertura: number
}

/** Reporte completo de una ventana de N horas. */
export interface Reporte {
  horas: number
  generado: Date
  filas: FilaReporte[]
  totalMinutos: number
  totalAperturas: number
  peorDeriva: FilaReporte
  puertasFuera: number
}
