/* ==== Analisis del video en vivo de una puerta ====
   Arranca el worker de visión sobre el stream en tiempo real de la cámara y
   deja los eventos de apertura y cierre en la base. Mientras corre, muestra lo
   que el worker va reportando. */

import { useCallback, useEffect, useRef, useState } from 'react'
import { detenerAnalisisVideo, estadoAnalisisVideo, iniciarAnalisisVideo } from '../lib/api'
import type { AnalisisWorker } from '../lib/api'
import { mmss } from '../lib/umbrales'

/** Cada cuánto se le pregunta al backend por el estado del worker. */
const SONDEO_MS = 3000

type Fase = 'idle' | 'lanzando' | 'corriendo' | 'deteniendo'

interface Props {
  puertaId: string
  onToast?: (mensaje: string) => void
}

export default function BotonAnalizarVideo({ puertaId, onToast }: Props) {
  const [fase, setFase] = useState<Fase>('idle')
  const [worker, setWorker] = useState<AnalisisWorker | null>(null)
  // Solo se puede pedir al arrancar: el visor lo abre el propio worker.
  const [conVisor, setConVisor] = useState(false)

  // El aviso se usa dentro de efectos: en una ref para no reiniciar el sondeo
  // cada vez que el padre se re-renderiza (el muro lo hace en cada poll).
  const avisar = useRef(onToast)
  avisar.current = onToast

  const consultar = useCallback(async () => {
    try {
      const data = await estadoAnalisisVideo(puertaId)
      setWorker(data.analisis)
      return data.corriendo
    } catch (error) {
      console.error('No se pudo consultar el estado del análisis:', error)
      return null // error de red: no se concluye nada, se reintenta
    }
  }, [puertaId])

  /* ---- Estado inicial ----
     El worker vive en el servidor, no en esta pestaña: si el operador recarga
     el muro con un análisis en marcha, el botón debe mostrarlo corriendo. */
  useEffect(() => {
    let montado = true
    void consultar().then((corriendo) => {
      if (montado && corriendo) setFase('corriendo')
    })
    return () => {
      montado = false
    }
  }, [consultar])

  /* ---- Sondeo mientras hay algo en marcha ---- */
  useEffect(() => {
    if (fase === 'idle') return

    const id = setInterval(() => {
      void consultar().then((corriendo) => {
        if (corriendo === null) return

        if (corriendo) {
          setFase('corriendo')
          return
        }

        // Dejó de estar vivo: terminó, se detuvo, o no llegó a arrancar. El
        // backend ya le dio su plazo de arranque antes de darlo por muerto.
        setFase('idle')
      })
    }, SONDEO_MS)

    return () => clearInterval(id)
  }, [fase, consultar])

  /* ---- El worker se cayó reportando el motivo ---- */
  const estadoWorker = worker?.estado
  const mensajeWorker = worker?.mensaje
  useEffect(() => {
    if (estadoWorker === 'error') {
      avisar.current?.(`El análisis no pudo continuar: ${mensajeWorker || 'error en el worker de visión'}`)
    }
  }, [estadoWorker, mensajeWorker])

  async function iniciar() {
    setFase('lanzando')

    try {
      const data = await iniciarAnalisisVideo(puertaId, conVisor)
      setWorker(data.analisis)
      avisar.current?.(data.message)

      // Al reservar el turno el backend ya responde `corriendo`, aunque el
      // worker siga cargando el modelo: eso se distingue por `analisis.estado`
      // y deja el botón listo para detener desde el primer momento.
      setFase(data.corriendo ? 'corriendo' : 'idle')
    } catch (error) {
      console.error('Error de red al iniciar el análisis:', error)
      avisar.current?.('No se pudo contactar al servidor para iniciar el análisis.')
      setFase('idle')
    }
  }

  async function detener() {
    setFase('deteniendo')
    try {
      const data = await detenerAnalisisVideo(puertaId)
      setWorker(data.analisis)
      avisar.current?.(data.message)
      if (!data.corriendo) setFase('idle')
    } catch (error) {
      console.error('Error de red al detener el análisis:', error)
      avisar.current?.('No se pudo contactar al servidor para detener el análisis.')
      setFase('corriendo')
    }
  }

  const ocupado = fase === 'lanzando' || fase === 'deteniendo'
  // El worker reserva su turno al instante pero tarda en cargar el modelo y
  // conectarse a la camara: mientras esta en eso se puede detener igual.
  const arrancando = fase === 'corriendo' && worker?.estado === 'iniciando'

  const texto =
    fase === 'lanzando'
      ? '⏳ Iniciando análisis...'
      : fase === 'deteniendo'
        ? '⏳ Cerrando evento en curso...'
        : arrancando
          ? '⏹ CANCELAR (cargando modelo...)'
          : fase === 'corriendo'
            ? '⏹ DETENER ANÁLISIS'
            : '🎥 ANALIZAR VIDEO'

  const estilo =
    ocupado || arrancando
      ? { background: 'var(--surface-2)', borderColor: 'var(--ring)' }
      : fase === 'corriendo'
        ? { background: 'var(--crit)', borderColor: 'var(--crit)' }
        : { background: '#1baf7a', borderColor: '#1baf7a' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
      <button
        className="btn"
        disabled={ocupado}
        title={
          fase === 'corriendo'
            ? 'Detiene el análisis y cierra el evento que esté en curso'
            : 'Analiza el video en tiempo real de la cámara y registra cada apertura en la base'
        }
        // El click no debe abrir el modal de la card que lo contiene.
        onClick={(ev) => {
          ev.stopPropagation()
          void (fase === 'corriendo' ? detener() : iniciar())
        }}
        style={{ ...estilo, color: 'white', fontWeight: 600, width: '100%', padding: 10 }}
      >
        {texto}
      </button>

      {fase === 'idle' ? (
        <label
          title="Abre una ventana con el video anotado (ROI, cajas y confianza) en el equipo del servidor. Cerrarla no detiene el análisis"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            color: 'var(--muted)',
            cursor: 'pointer',
          }}
          onClick={(ev) => ev.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={conVisor}
            onChange={(ev) => setConVisor(ev.target.checked)}
            style={{ accentColor: '#1baf7a', cursor: 'pointer' }}
          />
          Ver lo que ve el modelo
        </label>
      ) : (
        worker && <Detalle worker={worker} />
      )}
    </div>
  )
}

/** Lo que el worker reportó en su último latido. */
function Detalle({ worker }: { worker: AnalisisWorker }) {
  const zonas = worker.zonas ?? []

  return (
    <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.6 }}>
      {worker.estado === 'iniciando' && <div>{worker.mensaje || 'Iniciando...'}</div>}

      {zonas.map((z) => (
        <div key={z.nombre} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <span>{z.nombre}</span>
          <span style={{ color: z.estado === 'abierta' ? 'var(--warn)' : 'var(--good)' }}>
            {z.estado === 'abierta'
              ? `abierta ${mmss(z.segundos_abierta)} · conf ${z.confianza.toFixed(2)}`
              : 'cerrada'}
          </span>
        </div>
      ))}

      {worker.estado === 'corriendo' && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <span>
            {worker.eventos_registrados} evento(s) · {worker.fps_analisis} fps
          </span>
          <span>{worker.en_vivo ? 'cámara en vivo' : 'video local'}</span>
        </div>
      )}

      {worker.ventana && <div>👁 visor abierto en el equipo del servidor</div>}

      {worker.eventos_sin_enviar > 0 && (
        <div style={{ color: 'var(--warn)' }}>
          {worker.eventos_sin_enviar} evento(s) no llegaron a la base, quedaron respaldados en disco
        </div>
      )}

      {worker.reconexiones > 0 && <div>{worker.reconexiones} reconexión(es) a la cámara</div>}
    </div>
  )
}
