/* ==== Render del reporte general ==== */
const API_URL = 'http://localhost:8000'
let ventanaHoras = 12;
let reporte = null;

const colorDeriva = d => d > 6 ? 'var(--crit)' : d > 3 ? 'var(--serious)'
                        : d > 1.2 ? 'var(--warn)' : 'var(--good)';

const minTexto = m => m >= 60
  ? `${Math.floor(m/60)} h ${String(Math.round(m%60)).padStart(2,'0')} min`
  : `${m.toFixed(1)} min`;

/* ---- Tarjetas de resumen ---- */
function pintarKpis(){
  const r = reporte;
  const lider = r.filas[0];
  const termico = r.peorDeriva;
  // El dato interesante: no siempre son la misma puerta.
  const coinciden = lider.id === termico.id;

  document.getElementById('rep-kpis').innerHTML = `
    <div class="kpi">
      <div class="l">Tiempo total abierto</div>
      <div class="v">${(r.totalMinutos/60).toFixed(1)}<small> h</small></div>
      <div class="n">${r.totalAperturas} aperturas · ${FLOTA.length} puertas</div>
    </div>
    <div class="kpi">
      <div class="l">Más tiempo abierta</div>
      <div class="v" style="font-size:19px">${lider.id}</div>
      <div class="n">${minTexto(lider.minutos)} · ${lider.aperturas} aperturas</div>
    </div>
    <div class="kpi alerta">
      <div class="l">Mayor deriva térmica</div>
      <div class="v" style="font-size:19px">${termico.id}</div>
      <div class="n">+${termico.derivaMax} °C sobre set point${coinciden ? '' : ' · no es la más abierta'}</div>
    </div>
    <div class="kpi ${r.puertasFuera > 3 ? 'critico' : ''}">
      <div class="l">Puertas con deriva fuera de rango</div>
      <div class="v">${r.puertasFuera}<small> / ${FLOTA.length}</small></div>
      <div class="n">al menos una hora sobre 1,2 °C</div>
    </div>
    <div class="kpi">
      <div class="l">Promedio por apertura</div>
      <div class="v">${(r.totalMinutos/Math.max(1,r.totalAperturas)).toFixed(1)}<small> min</small></div>
      <div class="n">ventana de ${r.horas} h</div>
    </div>`;
}

/* ---- Hallazgo automático: ¿coinciden los dos rankings? ---- */
function pintarHallazgo(){
  const lider = reporte.filas[0];
  const termico = reporte.peorDeriva;
  const cont = document.getElementById('rep-hallazgo');

  if(lider.id === termico.id){
    cont.innerHTML = `<b>${lider.nombre}</b> lidera en tiempo abierto y además acumula la mayor
      deriva térmica (+${termico.derivaMax} °C). Es la puerta a intervenir primero.`;
    return;
  }

  cont.innerHTML = `La puerta más tiempo abierta no es la más castigada térmicamente.
    <b>${lider.nombre}</b> acumula ${minTexto(lider.minutos)} con +${lider.derivaMax} °C de deriva,
    mientras <b>${termico.nombre}</b> llega a <b>+${termico.derivaMax} °C</b> con solo
    ${minTexto(termico.minutos)} — su set point de ${termico.setPoint} °C deja un salto mucho
    mayor contra el ambiente, así que cada minuto abierta cuesta más. Para cadena de frío,
    priorizar por deriva y no por tiempo.`;
}

/* ---- Ranking: tabla donde la barra es el gráfico ---- */
function pintarRanking(){
  const filas = reporte.filas;
  const maxMin = Math.max(...filas.map(f => f.minutos), 1);
  const maxHora = Math.max(...filas.flatMap(f => f.serie.map(h => h.minutos)), 1);

  document.getElementById('rep-rank').innerHTML = `
    <table class="rank">
      <thead>
        <tr>
          <th></th><th>Puerta</th>
          <th style="min-width:150px">Tiempo abierto acumulado</th>
          <th class="num">Aperturas</th>
          <th class="num">Min/apertura</th>
          <th class="num">Deriva máx.</th>
          <th class="num">Temp. máx.</th>
          <th class="num">Horas fuera</th>
          <th style="min-width:110px">Por hora</th>
        </tr>
      </thead>
      <tbody>
        ${filas.map((f, i) => `
          <tr>
            <td class="pos">${i+1}</td>
            <td><div class="pnombre">${f.nombre}</div><div class="pzona">${f.zona} · set ${f.setPoint}°</div></td>
            <td>
              <div class="barra ${i===0 ? 'tope' : ''}">
                <i style="width:${(f.minutos/maxMin*100).toFixed(1)}%"></i>
                <span>${minTexto(f.minutos)}</span>
              </div>
            </td>
            <td class="num">${f.aperturas}</td>
            <td class="num">${f.minPorApertura}</td>
            <td class="num">
              <span class="deriva"><i style="background:${colorDeriva(f.derivaMax)}"></i>+${f.derivaMax} °C</span>
            </td>
            <td class="num">${f.tempMax} °C</td>
            <td class="num">${f.horasFuera} / ${reporte.horas}</td>
            <td>
              <div class="spark-h" role="img"
                   aria-label="Minutos abiertos por hora de ${f.nombre}, máximo ${Math.max(...f.serie.map(h=>h.minutos)).toFixed(1)} minutos">
                ${f.serie.map(h => {
                  const alto = Math.max(2, h.minutos / maxHora * 24);
                  const c = h.deriva > 6 ? 'var(--crit)' : h.deriva > 3 ? 'var(--serious)'
                          : h.deriva > 1.2 ? 'var(--warn)' : '#3a3a37';
                  return `<div style="height:${alto.toFixed(1)}px;background:${c}"
                               title="${String(h.hora).padStart(2,'0')}:00 · ${h.minutos} min · +${h.deriva} °C"></div>`;
                }).join('')}
              </div>
            </td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

/* ---- Render completo ---- */
function pintarReporte(){
  reporte = generarReporte(ventanaHoras);
  document.getElementById('rep-gen').textContent =
    'Generado ' + reporte.generado.toLocaleString('es-CL', { hour12:false });
  pintarKpis();
  pintarHallazgo();
  pintarRanking();
}

/* ---- Selector de ventana ---- */
document.getElementById('rep-ventana').addEventListener('click', ev => {
  const b = ev.target.closest('button');
  if(!b) return;
  ev.currentTarget.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
  ventanaHoras = +b.dataset.h;
  pintarReporte();
});

pintarReporte();
// Se regenera cada 5 minutos: los datos solo cambian al cruzar de hora.
setInterval(pintarReporte, 300000);
