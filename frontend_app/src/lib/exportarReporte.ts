/* ==== Exportación del reporte general ====
   Dos formatos, ninguna dependencia nueva:

   - CSV: para que las jefaturas lo abran en Excel y sigan cortando los datos.
     Separador ";" y decimales con coma, que es lo que espera un Excel con
     configuración regional es-CL, más BOM UTF-8 para que no rompa las tildes.

   - PDF: no se genera con una librería, se arma un documento HTML autónomo en
     tema claro (el muro es oscuro; imprimirlo gasta tóner y se ve mal) y se
     abre el diálogo de impresión del navegador, donde "Guardar como PDF" ya
     existe. Queda un archivo que se adjunta a un correo tal cual. */

import { minTexto } from './formato'
import { FLOTA } from './reportesDatos'
import type { Reporte } from '../types'

/* ---------- Utilidades comunes ---------- */

/** Número con coma decimal: lo que espera Excel en es-CL. */
const nc = (n: number, dec = 1): string => n.toFixed(dec).replace('.', ',')

/** Sello para el nombre de archivo: 2026-08-31_1430. */
function sello(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}`
}

const nombreBase = (r: Reporte) => `reporte-puertas-${r.horas}h-${sello(r.generado)}`

const fechaLarga = (d: Date) =>
  d.toLocaleString('es-CL', { dateStyle: 'long', timeStyle: 'short', hour12: false })

function descargar(contenido: BlobPart, nombre: string, tipo: string): void {
  const url = URL.createObjectURL(new Blob([contenido], { type: tipo }))
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  a.click()
  // El click es sincrónico, pero Firefox necesita que el objeto siga vivo un
  // instante más después de disparar la descarga.
  setTimeout(() => URL.revokeObjectURL(url), 4000)
}

/* ---------- CSV ---------- */

/** Comilla un campo solo si lo necesita (separador, comilla o salto de línea). */
const campo = (v: string | number): string => {
  const s = String(v)
  return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

const linea = (celdas: (string | number)[]) => celdas.map(campo).join(';')

/** Marca de orden de bytes: sin ella, Excel en Windows abre el CSV en ANSI y rompe las tildes. */
const BOM = '﻿'

export function exportarCSV(reporte: Reporte): void {
  const filas: string[] = [
    linea(['Reporte General · Puertas Cámaras de Frío']),
    linea(['Ventana', `Últimas ${reporte.horas} horas`]),
    linea(['Generado', fechaLarga(reporte.generado)]),
    linea(['Puertas monitoreadas', FLOTA.length]),
    '',
    linea(['Resumen']),
    linea(['Tiempo total abierto (h)', nc(reporte.totalMinutos / 60)]),
    linea(['Aperturas totales', reporte.totalAperturas]),
    linea(['Promedio por apertura (min)', nc(reporte.totalMinutos / Math.max(1, reporte.totalAperturas))]),
    linea(['Puerta más tiempo abierta', `${reporte.filas[0].id} — ${reporte.filas[0].nombre}`]),
    linea(['Mayor deriva térmica', `${reporte.peorDeriva.id} — ${reporte.peorDeriva.nombre}`]),
    linea(['Deriva máxima (°C)', nc(reporte.peorDeriva.derivaMax)]),
    linea(['Puertas con deriva fuera de rango', `${reporte.puertasFuera} de ${FLOTA.length}`]),
    '',
    linea(['Ranking por tiempo abierto']),
    linea([
      '#',
      'ID',
      'Puerta',
      'Zona',
      'Set point (°C)',
      'Minutos abiertos',
      'Aperturas',
      'Min/apertura',
      'Deriva máx. (°C)',
      'Temp. máx. (°C)',
      'Horas fuera de rango',
      'Horas de la ventana',
    ]),
  ]

  reporte.filas.forEach((f, i) => {
    filas.push(
      linea([
        i + 1,
        f.id,
        f.nombre,
        f.zona,
        nc(f.setPoint),
        nc(f.minutos),
        f.aperturas,
        nc(f.minPorApertura),
        nc(f.derivaMax),
        nc(f.tempMax),
        f.horasFuera,
        reporte.horas,
      ]),
    )
  })

  // Detalle hora a hora: es el dato que una jefatura pide después ("¿a qué hora
  // pasó?"), y en CSV no cuesta nada incluirlo.
  filas.push('', linea(['Detalle hora a hora']))
  filas.push(linea(['ID', 'Puerta', 'Hora', 'Aperturas', 'Minutos abiertos', 'Deriva (°C)', 'Temp. máx. (°C)']))
  for (const f of reporte.filas) {
    for (const h of f.serie) {
      filas.push(
        linea([
          f.id,
          f.nombre,
          `${String(h.hora).padStart(2, '0')}:00`,
          h.aperturas,
          nc(h.minutos),
          nc(h.deriva),
          nc(h.tempMax),
        ]),
      )
    }
  }

  filas.push('', linea(['Datos simulados — pendiente la identidad de puerta en el backend.']))

  descargar(BOM + filas.join('\r\n'), `${nombreBase(reporte)}.csv`, 'text/csv;charset=utf-8')
}

/* ---------- Documento imprimible / PDF ---------- */

const esc = (s: string | number): string =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

/** Colores de deriva en tema claro: los del muro no contrastan sobre blanco. */
const colorImpreso = (d: number): string =>
  d > 6 ? '#b3261e' : d > 3 ? '#c05621' : d > 1.2 ? '#8a6100' : '#1a7a3c'

function documentoHTML(reporte: Reporte): string {
  const lider = reporte.filas[0]
  const termico = reporte.peorDeriva
  const maxMin = Math.max(...reporte.filas.map((f) => f.minutos), 1)

  const kpi = (l: string, v: string, n: string, alerta = false) => `
    <div class="kpi">
      <div class="l">${esc(l)}</div>
      <div class="v"${alerta ? ' style="color:#b3261e"' : ''}>${v}</div>
      <div class="n">${esc(n)}</div>
    </div>`

  const hallazgo =
    lider.id === termico.id
      ? `<b>${esc(lider.nombre)}</b> lidera en tiempo abierto y además acumula la mayor deriva térmica
         (+${nc(termico.derivaMax)} °C). Es la puerta a intervenir primero.`
      : `La puerta más tiempo abierta no es la más castigada térmicamente.
         <b>${esc(lider.nombre)}</b> acumula ${esc(minTexto(lider.minutos))} con +${nc(lider.derivaMax)} °C de deriva,
         mientras <b>${esc(termico.nombre)}</b> llega a <b>+${nc(termico.derivaMax)} °C</b> con solo
         ${esc(minTexto(termico.minutos))} — su set point de ${nc(termico.setPoint)} °C deja un salto mucho mayor
         contra el ambiente, así que cada minuto abierta cuesta más. Para cadena de frío, priorizar por deriva y no
         por tiempo.`

  const cuerpo = reporte.filas
    .map(
      (f, i) => `
      <tr>
        <td class="pos">${i + 1}</td>
        <td><div class="pn">${esc(f.nombre)}</div><div class="pz">${esc(f.zona)} · set ${nc(f.setPoint)}°</div></td>
        <td>
          <div class="barra"><i style="width:${((f.minutos / maxMin) * 100).toFixed(1)}%"></i></div>
          <div class="bt">${esc(minTexto(f.minutos))}</div>
        </td>
        <td class="num">${f.aperturas}</td>
        <td class="num">${nc(f.minPorApertura)}</td>
        <td class="num" style="color:${colorImpreso(f.derivaMax)};font-weight:600">+${nc(f.derivaMax)} °C</td>
        <td class="num">${nc(f.tempMax)} °C</td>
        <td class="num">${f.horasFuera} / ${reporte.horas}</td>
      </tr>`,
    )
    .join('')

  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>${esc(nombreBase(reporte))}</title>
<style>
  @page { size: A4 landscape; margin: 14mm; }
  /* Las barras y los colores de estado son contenido, no decoración: hay que
     pedirle explícitamente al navegador que no los descarte al imprimir. */
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; padding: 24px; background: #fff; color: #16160f;
         font: 12px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
  .doc { max-width: 1050px; margin: 0 auto; }
  .cab { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px;
         border-bottom: 2px solid #16160f; padding-bottom: 12px; }
  h1 { font-size: 17px; margin: 0 0 3px; letter-spacing: -.2px; }
  .sub { font-size: 11.5px; color: #605e56; }
  .meta { font-size: 11px; color: #605e56; text-align: right; white-space: nowrap; }
  .meta b { color: #16160f; }
  .kpis { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }
  .kpi { flex: 1 1 150px; border: 1px solid #ddd9cf; border-radius: 8px; padding: 9px 11px; }
  .kpi .l { font-size: 9.5px; text-transform: uppercase; letter-spacing: .4px; color: #605e56; }
  .kpi .v { font-size: 20px; font-weight: 650; letter-spacing: -.5px; margin: 4px 0 2px;
            font-variant-numeric: tabular-nums; }
  .kpi .v small { font-size: 11px; font-weight: 500; color: #605e56; letter-spacing: 0; }
  .kpi .n { font-size: 10.5px; color: #605e56; }
  .hallazgo { border-left: 3px solid #c05621; background: #faf8f4; border-radius: 0 6px 6px 0;
              padding: 10px 13px; font-size: 11.5px; line-height: 1.6; margin-bottom: 14px; }
  h2 { font-size: 13px; margin: 0 0 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
  th { text-align: left; font-size: 9.5px; text-transform: uppercase; letter-spacing: .4px;
       color: #605e56; font-weight: 600; padding: 7px 8px; border-bottom: 1.5px solid #16160f;
       white-space: nowrap; }
  td { padding: 7px 8px; border-bottom: 1px solid #eceae3; vertical-align: middle; }
  tr { break-inside: avoid; }
  .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .pos { color: #918e85; width: 22px; font-variant-numeric: tabular-nums; }
  .pn { font-weight: 600; }
  .pz { font-size: 10px; color: #767368; margin-top: 1px; }
  .barra { height: 8px; min-width: 90px; background: #eceae3; border-radius: 4px; overflow: hidden; }
  .barra i { display: block; height: 100%; background: #2f6fbf; }
  .bt { font-size: 10.5px; color: #444239; margin-top: 3px; font-variant-numeric: tabular-nums; }
  .pie { margin-top: 18px; padding-top: 10px; border-top: 1px solid #eceae3;
         font-size: 10px; color: #767368; line-height: 1.6; }
  .pie code { font-family: ui-monospace, Consolas, monospace; }
  .acciones { max-width: 1050px; margin: 0 auto 14px; display: flex; gap: 8px; }
  .acciones button { font: inherit; font-size: 12px; padding: 8px 15px; border-radius: 8px;
                     border: 1px solid #16160f; background: #16160f; color: #fff; cursor: pointer; }
  .acciones button.sec { background: #fff; color: #16160f; }
  @media print { .acciones { display: none; } body { padding: 0; } }
</style>
</head>
<body>
<div class="acciones">
  <button onclick="window.print()">Imprimir / Guardar como PDF</button>
  <button class="sec" onclick="window.close()">Cerrar</button>
</div>
<div class="doc">
  <div class="cab">
    <div>
      <h1>Reporte General · Puertas Cámaras de Frío</h1>
      <div class="sub">Consolidado por cámara · ranking de exposición y deriva térmica</div>
    </div>
    <div class="meta">
      Ventana: <b>últimas ${reporte.horas} horas</b><br>
      Generado: <b>${esc(fechaLarga(reporte.generado))}</b><br>
      Puertas monitoreadas: <b>${FLOTA.length}</b>
    </div>
  </div>

  <div class="kpis">
    ${kpi(
      'Tiempo total abierto',
      `${nc(reporte.totalMinutos / 60)}<small> h</small>`,
      `${reporte.totalAperturas} aperturas · ${FLOTA.length} puertas`,
    )}
    ${kpi('Más tiempo abierta', esc(lider.id), `${minTexto(lider.minutos)} · ${lider.aperturas} aperturas`)}
    ${kpi(
      'Mayor deriva térmica',
      esc(termico.id),
      `+${nc(termico.derivaMax)} °C sobre set point${lider.id === termico.id ? '' : ' · no es la más abierta'}`,
      true,
    )}
    ${kpi(
      'Puertas fuera de rango',
      `${reporte.puertasFuera}<small> / ${FLOTA.length}</small>`,
      'al menos una hora sobre 1,2 °C',
      reporte.puertasFuera > 3,
    )}
    ${kpi(
      'Promedio por apertura',
      `${nc(reporte.totalMinutos / Math.max(1, reporte.totalAperturas))}<small> min</small>`,
      `ventana de ${reporte.horas} h`,
    )}
  </div>

  <h2>Ranking por tiempo abierto</h2>
  <div class="hallazgo">${hallazgo}</div>
  <table>
    <thead>
      <tr>
        <th></th><th>Puerta</th><th style="min-width:130px">Tiempo abierto acumulado</th>
        <th class="num">Aperturas</th><th class="num">Min/apertura</th><th class="num">Deriva máx.</th>
        <th class="num">Temp. máx.</th><th class="num">Horas fuera</th>
      </tr>
    </thead>
    <tbody>${cuerpo}</tbody>
  </table>

  <div class="pie">
    <b>Criterio de deriva:</b> se considera una hora fuera de rango cuando la temperatura estimada supera en más de
    1,2 °C el set point de la cámara. Los colores de la columna de deriva marcan los tramos 1,2 / 3 / 6 °C.<br>
    <b>Datos simulados.</b> El backend todavía no registra identidad de puerta en <code>EventoPuerta</code>, así que
    el consolidado por cámara se genera de forma determinista en el frontend. La deriva térmica se deriva de los
    minutos abiertos con la misma saturación exponencial del modelo de temperatura, no se sortea.
  </div>
</div>
</body>
</html>`
}

/**
 * Abre el reporte imprimible en una pestaña nueva. Si el bloqueador de pop-ups
 * lo impide, cae a descargar el .html — así el usuario nunca se queda sin nada.
 * Devuelve false cuando hubo que caer a la descarga, para poder avisarlo.
 */
export function exportarPDF(reporte: Reporte): boolean {
  const html = documentoHTML(reporte)
  const ventana = window.open('', '_blank')
  if (!ventana) {
    descargar(html, `${nombreBase(reporte)}.html`, 'text/html;charset=utf-8')
    return false
  }
  ventana.document.write(html)
  ventana.document.close()
  return true
}
