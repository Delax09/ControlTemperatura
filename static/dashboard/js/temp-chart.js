/* ==== Gráfico de temperatura del modal ====
   Serie única de una medida continua en el tiempo -> gráfico de línea.

   Color: la línea usa el acento azul (--blue), que no es un color de estado.
   Los tonos cálidos quedan reservados para la banda de umbral, que es donde el
   color sí comunica estado. Contraste de #3987e5 sobre #232321 = 4,33:1. */

const G = {            // geometría en unidades del viewBox
  W: 520, H: 150,
  x0: 40, x1: 510,
  y0: 12, y1: 124,
};
const DERIVA_UMBRAL = 5.0;   // °C fuera de set point que ya se considera deriva

/* Escala vertical con topes redondeados a múltiplos de 5. */
function escalaY(valores, setPoint){
  const min = Math.min(...valores, setPoint);
  const max = Math.max(...valores, setPoint);
  const holgura = Math.max(1, (max - min) * 0.12);
  let lo = Math.floor((min - holgura) / 5) * 5;
  let hi = Math.ceil((max + holgura) / 5) * 5;
  if(hi - lo < 10) hi = lo + 10;
  return [lo, hi];
}

const hhmmCorto = d => d.toLocaleTimeString('es-CL', { hour12:false }).slice(0,5);

/* Dibuja el gráfico dentro de `cont` y conecta el hover. */
function renderGraficoTemp(cont, serie, setPoint){
  if(!serie || serie.length < 2){
    cont.innerHTML = '<div class="g-vacio">Sin lecturas de temperatura todavía</div>';
    return;
  }

  const vals = serie.map(p => p.v);
  const [lo, hi] = escalaY(vals, setPoint);
  const px = i => G.x0 + i / (serie.length - 1) * (G.x1 - G.x0);
  const py = v => G.y1 - (v - lo) / (hi - lo) * (G.y1 - G.y0);

  // --- grilla y etiquetas del eje Y ---
  const pasos = 4;
  let grilla = '';
  for(let k = 0; k <= pasos; k++){
    const v = lo + (hi - lo) * k / pasos;
    const y = py(v);
    grilla += `<line class="g-grid" x1="${G.x0}" y1="${y.toFixed(1)}" x2="${G.x1}" y2="${y.toFixed(1)}"/>`
            +  `<text class="g-ylab" x="${G.x0 - 7}" y="${(y + 3).toFixed(1)}">${v.toFixed(0)}°</text>`;
  }

  // --- banda de umbral: por sobre set point + deriva ---
  const yUmbral = py(setPoint + DERIVA_UMBRAL);
  const banda = yUmbral > G.y0
    ? `<rect class="g-banda" x="${G.x0}" y="${G.y0}" width="${G.x1 - G.x0}" height="${(yUmbral - G.y0).toFixed(1)}"/>
        <text class="g-umbral" x="${G.x1 - 4}" y="${(G.y0 + 10).toFixed(1)}">fuera de rango</text>`
    : '';

  // --- línea de referencia del set point ---
  const ySet = py(setPoint);
  const refSet = (ySet >= G.y0 && ySet <= G.y1)
    ? `<line class="g-set" x1="${G.x0}" y1="${ySet.toFixed(1)}" x2="${G.x1}" y2="${ySet.toFixed(1)}"/>
        <text class="g-setlab" x="${G.x0 + 4}" y="${(ySet - 5).toFixed(1)}">set point ${setPoint}°</text>`
    : '';

  // --- serie ---
  const puntos = serie.map((p, i) => `${px(i).toFixed(1)},${py(p.v).toFixed(1)}`).join(' ');
  const area = `${G.x0},${G.y1} ${puntos} ${G.x1},${G.y1}`;

  // --- etiquetas del eje X cada 15 minutos ---
  let xlabs = '';
  for(let i = 0; i < serie.length; i += 15){
    xlabs += `<text class="g-xlab" x="${px(i).toFixed(1)}" y="${G.H - 4}">${hhmmCorto(serie[i].t)}</text>`;
  }
  const ult = serie.length - 1;
  xlabs += `<text class="g-xlab g-ahora" x="${px(ult).toFixed(1)}" y="${G.H - 4}">ahora</text>`;

  cont.innerHTML = `
    <svg class="g-svg" viewBox="0 0 ${G.W} ${G.H}" role="img"
          aria-label="Temperatura interior de los últimos ${serie.length} minutos, entre ${Math.min(...vals).toFixed(1)} y ${Math.max(...vals).toFixed(1)} grados, con set point en ${setPoint} grados">
      <defs>
        <linearGradient id="gTempFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#3987e5" stop-opacity=".28"/>
          <stop offset="1" stop-color="#3987e5" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${banda}
      ${grilla}
      ${refSet}
      <polygon class="g-area" points="${area}" fill="url(#gTempFill)"/>
      <polyline class="g-linea" points="${puntos}"/>
      <circle class="g-fin" cx="${px(ult).toFixed(1)}" cy="${py(serie[ult].v).toFixed(1)}" r="4.5"/>
      <line class="g-cruz" id="g-cruz" x1="0" y1="${G.y0}" x2="0" y2="${G.y1}" style="display:none"/>
      <circle class="g-hover" id="g-hover" r="4.5" style="display:none"/>
      ${xlabs}
    </svg>
    <div class="g-tip" id="g-tip" role="status" aria-live="polite"></div>`;

  // --- capa de hover: crosshair + tooltip ---
  const svg  = cont.querySelector('.g-svg');
  const cruz = cont.querySelector('#g-cruz');
  const mark = cont.querySelector('#g-hover');
  const tip  = cont.querySelector('#g-tip');

  function mover(ev){
    const r = svg.getBoundingClientRect();
    const fx = (ev.clientX - r.left) / r.width * G.W;
    let i = Math.round((fx - G.x0) / (G.x1 - G.x0) * (serie.length - 1));
    i = Math.max(0, Math.min(serie.length - 1, i));

    const p = serie[i];
    const x = px(i), y = py(p.v);

    cruz.setAttribute('x1', x); cruz.setAttribute('x2', x);
    cruz.style.display = '';
    mark.setAttribute('cx', x); mark.setAttribute('cy', y);
    mark.style.display = '';

    const fuera = Math.abs(p.v - setPoint) > DERIVA_UMBRAL;
    tip.innerHTML = `<b>${p.v.toFixed(1)} °C</b><span>${hhmmCorto(p.t)}</span>`
                  + (fuera ? '<em>fuera de rango</em>' : '');
    tip.classList.add('on');
    // Posición en porcentaje para seguir el escalado del SVG, acotada a los
    // bordes para que no se desborde del contenedor en los extremos.
    const izq = Math.max(14, Math.min(86, x / G.W * 100));
    tip.style.left = izq + '%';
    tip.style.top  = Math.max(0, y / G.H * 100) + '%';
  }

  function salir(){
    cruz.style.display = 'none';
    mark.style.display = 'none';
    tip.classList.remove('on');
  }

  svg.addEventListener('mousemove', mover);
  svg.addEventListener('mouseleave', salir);
  svg.addEventListener('touchmove', ev => {
    if(ev.touches[0]) mover(ev.touches[0]);
  }, { passive:true });
  svg.addEventListener('touchend', salir);
}
