/* ==== Modal de detalle de puerta / centro de alertas ====
   Se abre al hacer click en una card del muro. Todo lo que muestra se deriva
   de los datos reales de la puerta; los campos que el backend todavía no
   entrega se marcan explícitamente como pendientes en vez de inventar valores.

   El componente nunca se desmonta (el muro lo renderiza siempre y le pasa
   `puerta = null` cuando está cerrado), así las notas del turno sobreviven a
   abrir y cerrar el modal. */

import { useEffect, useRef, useState } from 'react'
import EscaleraEscalamiento from './EscaleraEscalamiento'
import Bitacora, { type NotaTurno } from './Bitacora'
import PanelTemperatura from './PanelTemperatura'
import HistorialAperturas from './HistorialAperturas'
import TempChart from './TempChart'
import { COLOR, NIVEL_NOMBRE, REGLAS_ESCALAMIENTO, hhmm, mmss, nivelDe } from '../lib/umbrales'
import { serieDe } from '../lib/tempSim'
import type { Puerta } from '../types'

const ACCIONES = [
  { clase: 'btn pri', label: '📻 Radio al andén', accion: 'Radio abierta con el andén · canal 3' },
  { clase: 'btn', label: '💬 WhatsApp operaciones', accion: 'Mensaje enviado al grupo «Operaciones PSP»' },
  { clase: 'btn', label: '📎 Adjuntar clip', accion: 'Snapshot y clip de 60 s adjuntados al incidente' },
]

interface Props {
  puerta: Puerta | null
  /** Momento en que llegaron los últimos datos de la API. */
  ultimaActualizacion: number
  onCerrar: () => void
  onSilenciar: (id: string) => void
  onToast: (texto: string) => void
}

export default function ModalAlerta({ puerta, ultimaActualizacion, onCerrar, onSilenciar, onToast }: Props) {
  const dlg = useRef<HTMLDialogElement>(null)
  const [, setTick] = useState(0)
  const [notas, setNotas] = useState<Record<string, NotaTurno[]>>({})
  const [borrador, setBorrador] = useState('')
  const escalonesPrevios = useRef<number | null>(null)

  /* ---- Apertura y cierre del <dialog> nativo ---- */
  useEffect(() => {
    const d = dlg.current
    if (!d) return
    if (puerta && !d.open) d.showModal()
    if (!puerta && d.open) d.close()
  }, [puerta])

  /* ---- Cronómetro: un repintado por segundo mientras está abierto ---- */
  useEffect(() => {
    if (!puerta) return
    const id = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [puerta])

  /* ---- El borrador de la nota se recarga al cambiar de puerta ---- */
  const idPuerta = puerta?.id
  useEffect(() => {
    escalonesPrevios.current = null
    setBorrador('')
  }, [idPuerta])

  // Segundos abiertos "en vivo": el dato del backend más lo transcurrido desde
  // que llegó, para que el cronómetro no se congele entre polls de 5 s.
  const segundos = puerta?.abierta
    ? puerta.segundos_abierta + Math.max(0, (Date.now() - ultimaActualizacion) / 1000)
    : 0

  // Aviso al cruzar un escalón nuevo de la escalera de escalamiento.
  const escalones = REGLAS_ESCALAMIENTO.filter((r) => segundos > r.t).length
  useEffect(() => {
    if (!puerta) return
    const previos = escalonesPrevios.current
    if (previos !== null && escalones > previos && puerta.abierta) {
      onToast('Escalamiento: ' + REGLAS_ESCALAMIENTO[escalones - 1].titulo + ' · ' + puerta.nombre)
    }
    escalonesPrevios.current = escalones
  }, [escalones, puerta, onToast])

  function guardarNota() {
    const v = borrador.trim()
    if (!v || !puerta) return
    const nota: NotaTurno = { hora: hhmm(new Date()), texto: v }
    setNotas((previas) => ({ ...previas, [puerta.id]: [...(previas[puerta.id] ?? []), nota] }))
    onToast('Nota guardada en el incidente')
  }

  const n = puerta ? nivelDe(segundos, puerta.abierta) : 'ok'
  const deriva = puerta ? puerta.temp_actual - puerta.temp_objetivo : 0

  return (
    <dialog
      className="modal"
      ref={dlg}
      aria-labelledby="m-titulo"
      // Escape cierra el <dialog> por sí solo; hay que avisarle al muro.
      onClose={onCerrar}
      // Click en el backdrop (fuera del contenido) también cierra.
      onClick={(ev) => {
        if (ev.target === dlg.current) onCerrar()
      }}
    >
      {puerta && (
        <>
          <div className="m-head">
            <div className="who">
              <h2 id="m-titulo">
                {puerta.nombre} <span className="id">· {puerta.id}</span>
              </h2>
              <div className="zona">
                {puerta.zona} · set point {puerta.temp_objetivo} °C · cámara {puerta.cam || '—'}
              </div>
              <div className="m-chips">
                <span className="m-chip" style={{ borderColor: COLOR[n], color: COLOR[n] }}>
                  ▲ {NIVEL_NOMBRE[n]}
                </span>
                <span className="m-chip">{puerta.abierta ? 'Abierta' : 'Cerrada'}</span>
                <span className="m-chip">
                  Δt {deriva >= 0 ? '+' : ''}
                  {deriva.toFixed(1)}°
                </span>
                <span className="m-chip">{puerta.aperturas_hoy} aperturas hoy</span>
                {puerta.offline && (
                  <span className="m-chip" style={{ borderColor: 'var(--crit)', color: 'var(--crit)' }}>
                    Sin señal
                  </span>
                )}
                <span className="m-chip pend">Causa: pendiente</span>
              </div>
            </div>
            <div className="m-big">
              <div className="n" style={{ color: puerta.abierta ? COLOR[n] : 'var(--ink-2)' }}>
                {puerta.abierta ? mmss(segundos) : '—'}
              </div>
              <div className="c">{puerta.abierta ? 'puerta abierta ahora' : 'puerta cerrada'}</div>
            </div>
            <button className="m-close" aria-label="Cerrar detalle" onClick={onCerrar}>
              ✕
            </button>
          </div>

          <div className="m-actions">
            {ACCIONES.map((a) => (
              <button key={a.accion} className={a.clase} onClick={() => onToast(a.accion)}>
                {a.label}
              </button>
            ))}
            <button
              className="btn"
              onClick={() => {
                onSilenciar(puerta.id)
                onToast('Alerta silenciada 5 minutos · ' + puerta.nombre)
              }}
            >
              Silenciar 5 min
            </button>
          </div>

          <div className="m-body">
            <div className="m-col">
              <div className="m-lab">Escalera de escalamiento</div>
              <EscaleraEscalamiento segundos={segundos} abierta={puerta.abierta} />

              <div className="m-lab">Nota para el turno</div>
              <textarea
                className="m-note"
                value={borrador}
                onChange={(ev) => setBorrador(ev.target.value)}
                placeholder="Ej.: cortina rápida del andén 1 con sensor desalineado, avisar a mantención…"
              />
              <button className="btn" style={{ marginTop: 9 }} onClick={guardarNota}>
                Guardar nota
              </button>
            </div>

            <div className="m-col">
              <div className="m-lab">Bitácora del evento</div>
              <Bitacora puerta={puerta} segundos={segundos} notas={notas[puerta.id] ?? []} />

              <div className="m-lab">Temperatura · última hora</div>
              <TempChart serie={serieDe(puerta)} setPoint={puerta.temp_objetivo} />
              <PanelTemperatura puerta={puerta} serie={serieDe(puerta)} />

              <div className="m-lab">Últimas aperturas</div>
              <HistorialAperturas historial={puerta.historial_aperturas ?? []} />
            </div>
          </div>

          <div className="m-foot">
            Escalera y bitácora derivadas del tiempo real de apertura. Las acciones son de demostración.
          </div>
        </>
      )}
    </dialog>
  )
}
