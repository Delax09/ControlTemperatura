/* ==== Ranking: tabla donde la barra es el gráfico ==== */

import { colorDeriva, colorDerivaBarra, minTexto } from '../../lib/formato'
import type { Reporte } from '../../types'

export default function RankingTable({ reporte }: { reporte: Reporte }) {
  const filas = reporte.filas
  const maxMin = Math.max(...filas.map((f) => f.minutos), 1)
  const maxHora = Math.max(...filas.flatMap((f) => f.serie.map((h) => h.minutos)), 1)

  return (
    <div className="tabla-wrap">
      <table className="rank">
        <thead>
          <tr>
            <th />
            <th>Puerta</th>
            <th style={{ minWidth: 150 }}>Tiempo abierto acumulado</th>
            <th className="num">Aperturas</th>
            <th className="num">Min/apertura</th>
            <th className="num">Deriva máx.</th>
            <th className="num">Temp. máx.</th>
            <th className="num">Horas fuera</th>
            <th style={{ minWidth: 110 }}>Por hora</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={f.id}>
              <td className="pos">{i + 1}</td>
              <td>
                <div className="pnombre">{f.nombre}</div>
                <div className="pzona">
                  {f.zona} · set {f.setPoint}°
                </div>
              </td>
              <td>
                <div className={`barra${i === 0 ? ' tope' : ''}`}>
                  <i style={{ width: `${((f.minutos / maxMin) * 100).toFixed(1)}%` }} />
                  <span>{minTexto(f.minutos)}</span>
                </div>
              </td>
              <td className="num">{f.aperturas}</td>
              <td className="num">{f.minPorApertura}</td>
              <td className="num">
                <span className="deriva">
                  <i style={{ background: colorDeriva(f.derivaMax) }} />+{f.derivaMax} °C
                </span>
              </td>
              <td className="num">{f.tempMax} °C</td>
              <td className="num">
                {f.horasFuera} / {reporte.horas}
              </td>
              <td>
                <div
                  className="spark-h"
                  role="img"
                  aria-label={`Minutos abiertos por hora de ${f.nombre}, máximo ${Math.max(
                    ...f.serie.map((h) => h.minutos),
                  ).toFixed(1)} minutos`}
                >
                  {f.serie.map((h) => (
                    <div
                      key={h.hAbs}
                      style={{
                        // Número, no string: React solo agrega "px" a los números.
                        height: +Math.max(2, (h.minutos / maxHora) * 24).toFixed(1),
                        background: colorDerivaBarra(h.deriva),
                      }}
                      title={`${String(h.hora).padStart(2, '0')}:00 · ${h.minutos} min · +${h.deriva} °C`}
                    />
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
