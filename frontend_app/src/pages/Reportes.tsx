/* ==== Reporte general ====
   Equivalente de la antigua reportes.html + reportes.js. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Kpis from '../components/reportes/Kpis'
import Hallazgo from '../components/reportes/Hallazgo'
import RankingTable from '../components/reportes/RankingTable'
import { generarReporte } from '../lib/reportesDatos'

const VENTANAS = [6, 12, 24]
/** Los datos solo cambian al cruzar de hora, así que basta regenerar cada 5 min. */
const REFRESCO_MS = 300000

export default function Reportes() {
  const [horas, setHoras] = useState(12)
  const [reporte, setReporte] = useState(() => generarReporte(12))

  useEffect(() => {
    setReporte(generarReporte(horas))
    const id = setInterval(() => setReporte(generarReporte(horas)), REFRESCO_MS)
    return () => clearInterval(id)
  }, [horas])

  return (
    <div className="rep">
      <div className="rep-head">
        <div>
          <h1>Reporte General · Puertas Cámaras de Frío</h1>
          <div className="sub">Consolidado por cámara · ranking de exposición y deriva térmica</div>
        </div>
        <Link className="rep-volver" to="/">
          ← Volver al muro de control
        </Link>
      </div>

      <div className="rep-filtros">
        <span className="lbl">Ventana</span>
        <div className="seg">
          {VENTANAS.map((h) => (
            <button key={h} aria-pressed={horas === h} onClick={() => setHoras(h)}>
              {h} horas
            </button>
          ))}
        </div>
        <span className="rep-gen">Generado {reporte.generado.toLocaleString('es-CL', { hour12: false })}</span>
      </div>

      <Kpis reporte={reporte} />

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Ranking por tiempo abierto</h2>
            <div className="hint">
              Ordenado por minutos acumulados. La última columna muestra el detalle hora a hora.
            </div>
          </div>
        </div>
        <div className="panel-body">
          <Hallazgo reporte={reporte} />
          <RankingTable reporte={reporte} />
        </div>
      </div>

      <div className="panel">
        <div className="panel-body" style={{ paddingTop: 16 }}>
          <div className="rep-nota">
            <b>Datos simulados.</b> El backend todavía no tiene identidad de puerta en <code>EventoPuerta</code>, así
            que no existe de dónde leer un consolidado por cámara. La simulación vive en{' '}
            <code>src/lib/reportesDatos.ts</code> y es determinista: los mismos valores salen siempre y solo cambian al
            cruzar de hora, para que el ranking no se reordene solo. La deriva térmica no se sortea — se deriva de los
            minutos abiertos con la misma saturación exponencial que usa <code>src/lib/tempSim.ts</code>, así que el
            ranking y la temperatura son coherentes entre sí.
          </div>
        </div>
      </div>
    </div>
  )
}
