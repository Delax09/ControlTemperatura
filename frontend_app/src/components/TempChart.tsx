/* ==== Gráfico de temperatura del modal ====
   Serie única de una medida continua en el tiempo -> gráfico de línea.

   Color: la línea usa el acento azul (--blue), que no es un color de estado.
   Los tonos cálidos quedan reservados para la banda de umbral, que es donde el
   color sí comunica estado. Contraste de #3987e5 sobre #232321 = 4,33:1. */

import { useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { hhmm } from '../lib/umbrales'
import type { Muestra } from '../types'

const G = {
  // geometría en unidades del viewBox
  W: 520,
  H: 150,
  x0: 40,
  x1: 510,
  y0: 12,
  y1: 124,
}
const DERIVA_UMBRAL = 5.0 // °C fuera de set point que ya se considera deriva

/** Escala vertical con topes redondeados a múltiplos de 5. */
function escalaY(valores: number[], setPoint: number): [number, number] {
  const min = Math.min(...valores, setPoint)
  const max = Math.max(...valores, setPoint)
  const holgura = Math.max(1, (max - min) * 0.12)
  const lo = Math.floor((min - holgura) / 5) * 5
  let hi = Math.ceil((max + holgura) / 5) * 5
  if (hi - lo < 10) hi = lo + 10
  return [lo, hi]
}

interface Props {
  serie: Muestra[]
  setPoint: number
}

export default function TempChart({ serie, setPoint }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)

  if (!serie || serie.length < 2) {
    return (
      <div className="g-wrap">
        <div className="g-vacio">Sin lecturas de temperatura todavía</div>
      </div>
    )
  }

  const vals = serie.map((p) => p.v)
  const [lo, hi] = escalaY(vals, setPoint)
  const px = (i: number) => G.x0 + (i / (serie.length - 1)) * (G.x1 - G.x0)
  const py = (v: number) => G.y1 - ((v - lo) / (hi - lo)) * (G.y1 - G.y0)

  // --- grilla y etiquetas del eje Y ---
  const pasos = 4
  const grilla = Array.from({ length: pasos + 1 }, (_, k) => {
    const v = lo + ((hi - lo) * k) / pasos
    const y = py(v)
    return (
      <g key={`g${k}`}>
        <line className="g-grid" x1={G.x0} y1={y.toFixed(1)} x2={G.x1} y2={y.toFixed(1)} />
        <text className="g-ylab" x={G.x0 - 7} y={(y + 3).toFixed(1)}>
          {v.toFixed(0)}°
        </text>
      </g>
    )
  })

  // --- banda de umbral: por sobre set point + deriva ---
  const yUmbral = py(setPoint + DERIVA_UMBRAL)

  // --- línea de referencia del set point ---
  const ySet = py(setPoint)

  // --- serie ---
  const puntos = serie.map((p, i) => `${px(i).toFixed(1)},${py(p.v).toFixed(1)}`).join(' ')
  const area = `${G.x0},${G.y1} ${puntos} ${G.x1},${G.y1}`

  // --- etiquetas del eje X cada 15 minutos ---
  const xlabs: ReactNode[] = []
  for (let i = 0; i < serie.length; i += 15) {
    xlabs.push(
      <text key={`x${i}`} className="g-xlab" x={px(i).toFixed(1)} y={G.H - 4}>
        {hhmm(serie[i].t)}
      </text>,
    )
  }
  const ult = serie.length - 1

  /** Índice de la muestra bajo el cursor, en coordenadas del viewBox. */
  function mover(clientX: number) {
    const svg = svgRef.current
    if (!svg) return
    const r = svg.getBoundingClientRect()
    const fx = ((clientX - r.left) / r.width) * G.W
    let i = Math.round(((fx - G.x0) / (G.x1 - G.x0)) * (serie.length - 1))
    i = Math.max(0, Math.min(serie.length - 1, i))
    setHover(i)
  }

  const p = hover !== null ? serie[hover] : null
  const hx = hover !== null ? px(hover) : 0
  const hy = p ? py(p.v) : 0
  const fuera = p ? Math.abs(p.v - setPoint) > DERIVA_UMBRAL : false

  return (
    <div className="g-wrap">
      <svg
        ref={svgRef}
        className="g-svg"
        viewBox={`0 0 ${G.W} ${G.H}`}
        role="img"
        aria-label={`Temperatura interior de los últimos ${serie.length} minutos, entre ${Math.min(...vals).toFixed(1)} y ${Math.max(...vals).toFixed(1)} grados, con set point en ${setPoint} grados`}
        onMouseMove={(ev) => mover(ev.clientX)}
        onMouseLeave={() => setHover(null)}
        onTouchMove={(ev) => ev.touches[0] && mover(ev.touches[0].clientX)}
        onTouchEnd={() => setHover(null)}
      >
        <defs>
          <linearGradient id="gTempFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3987e5" stopOpacity=".28" />
            <stop offset="1" stopColor="#3987e5" stopOpacity="0" />
          </linearGradient>
        </defs>

        {yUmbral > G.y0 && (
          <>
            <rect className="g-banda" x={G.x0} y={G.y0} width={G.x1 - G.x0} height={(yUmbral - G.y0).toFixed(1)} />
            <text className="g-umbral" x={G.x1 - 4} y={(G.y0 + 10).toFixed(1)}>
              fuera de rango
            </text>
          </>
        )}

        {grilla}

        {ySet >= G.y0 && ySet <= G.y1 && (
          <>
            <line className="g-set" x1={G.x0} y1={ySet.toFixed(1)} x2={G.x1} y2={ySet.toFixed(1)} />
            <text className="g-setlab" x={G.x0 + 4} y={(ySet - 5).toFixed(1)}>
              set point {setPoint}°
            </text>
          </>
        )}

        <polygon className="g-area" points={area} fill="url(#gTempFill)" />
        <polyline className="g-linea" points={puntos} />
        <circle className="g-fin" cx={px(ult).toFixed(1)} cy={py(serie[ult].v).toFixed(1)} r="4.5" />

        <line className="g-cruz" x1={hx} y1={G.y0} x2={hx} y2={G.y1} style={{ display: p ? '' : 'none' }} />
        <circle className="g-hover" cx={hx} cy={hy} r="4.5" style={{ display: p ? '' : 'none' }} />

        {xlabs}
        <text className="g-xlab g-ahora" x={px(ult).toFixed(1)} y={G.H - 4}>
          ahora
        </text>
      </svg>

      {/* Posición en porcentaje para seguir el escalado del SVG, acotada a los
          bordes para que no se desborde del contenedor en los extremos. */}
      <div
        className={`g-tip${p ? ' on' : ''}`}
        role="status"
        aria-live="polite"
        style={{
          left: `${Math.max(14, Math.min(86, (hx / G.W) * 100))}%`,
          top: `${Math.max(0, (hy / G.H) * 100)}%`,
        }}
      >
        {p && (
          <>
            <b>{p.v.toFixed(1)} °C</b>
            <span>{hhmm(p.t)}</span>
            {fuera && <em>fuera de rango</em>}
          </>
        )}
      </div>
    </div>
  )
}
