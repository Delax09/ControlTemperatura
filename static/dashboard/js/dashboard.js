/* ==== Constantes ==== */
const UMBRAL_WARN = 180;   // 3 min
const UMBRAL_SER  = 300;   // 5 min
const UMBRAL_CRIT = 420;   // 7 min

const COLOR = { ok:'var(--good)', open:'var(--warn)', warn:'var(--warn)', serious:'var(--serious)', crit:'var(--crit)' };
const mmss = s => String(Math.floor(s/60)).padStart(2,'0')+':'+String(Math.floor(s%60)).padStart(2,'0');

/* ==== Estado Global ==== */
let estado = [];
const grid = document.getElementById('grid');

/* ==== Conexión a la API (Django) ==== */
async function fetchDatosBackend() {
  try {
    // Aquí defines la URL de tu endpoint de Django REST Framework
    // Ejemplo esperado del JSON de respuesta:
    // [
    //   {
    //     "id": "PSP-01",
    //     "nombre": "ANDÉN PSP 1",
    //     "zona": "Andén despacho",
    //     "cam": "anden1",
    //     "tipo": "anden",
    //     "temp_objetivo": -0.5,
    //     "temp_actual": -0.2,
    //     "abierta": true,
    //     "segundos_abierta": 240,
    //     "aperturas_hoy": 15,
    //     "minutos_hoy": 42.5,
    //     "offline": false,
    //     "historial_aperturas": [120, 300, 45, ...],
    //     "ack": 0
    //   }
    // ]
    const response = await fetch('/api/eventos-camaras/');

    if (response.ok) {
      estado = await response.json();
      render();
    } else {
      console.warn("La API no devolvió un estado OK. Usando datos de prueba mientras se conecta el endpoint real.");
      usarDatosDePrueba();
    }
  } catch (error) {
    console.error("Error al conectarse a la API de Django:", error);
    usarDatosDePrueba();
  }
}

// El backend todavía no expone /api/eventos-camaras/ con el formato que
// espera este dashboard (ver comentario más arriba). Mientras se conecta,
// se usa un dato de prueba fijo para poder seguir probando la UI y el
// botón de arranque del modelo YOLO.
function usarDatosDePrueba(){
  if(estado.length === 0) {
    estado = [{
      id: 'PSP-01', nombre: 'ANDÉN PSP 1', zona: 'Andén despacho', cam: 'anden1', tipo: 'anden',
      temp_objetivo: -20.0, temp_actual: -19.5, abierta: true, segundos_abierta: 190,
      aperturas_hoy: 10, minutos_hoy: 15.2, offline: false, historial_aperturas: [40, 150, 400], ack: 0
    }];
    render();
  }
}

/* ==== Renderizado ==== */
function nivel(e){
  if(!e.abierta) return 'ok';
  if(e.segundos_abierta >= UMBRAL_CRIT) return 'crit';
  if(e.segundos_abierta >= UMBRAL_SER)  return 'serious';
  if(e.segundos_abierta >= UMBRAL_WARN) return 'warn';
  return 'open';
}

function cardHTML(e){
  const n = nivel(e);
  const badge = !e.abierta
      ? '<span class="badge b-closed">● CERRADA</span>'
      : n==='crit'  ? '<span class="badge b-crit">▲ FALTA · PUERTA ABIERTA</span>'
      : n==='serious'? '<span class="badge b-serious">▲ ABIERTA PROLONGADA</span>'
      : '<span class="badge b-open">◐ ABIERTA</span>';

  const pct = Math.min(100, e.abierta ? e.segundos_abierta/UMBRAL_CRIT*100 : 0);
  const drift = Math.abs(e.temp_actual - e.temp_objetivo) > 1.2;
  const maxh = e.historial_aperturas && e.historial_aperturas.length ? Math.max(...e.historial_aperturas) : 1;

  return `
  <article class="card" data-state="${n}" data-id="${e.id}" data-open="${e.abierta?1:0}">
    <div class="cam">
      ${e.cam && CAM_THUMBS[e.cam] ? `<img src="${CAM_THUMBS[e.cam]}" alt="">` : placeholderCam(e.tipo)}
      <div class="noise"></div><div class="scrim"></div>
      <div class="osd">${e.nombre}</div>
      <div class="rec"><i></i>REC · ${e.id}</div>
      <div class="doorstate">${badge}</div>
      <div class="timer" style="color:${e.abierta?COLOR[n]:'var(--ink-2)'}">${e.abierta ? mmss(e.segundos_abierta) : '—'}</div>
    </div>
    <div class="body">
      <div class="rowtop">
        <div><div class="name">${e.nombre}</div><div class="zone">${e.zona}</div></div>
        <div class="temp ${drift?'drift':''}"><b>${e.temp_actual.toFixed(1)}°</b><small>set ${e.temp_objetivo}°</small></div>
      </div>
      <div class="slabar">
        <div class="slalabels"><span>Tiempo vs. umbral operacional</span><span class="cnt">${e.abierta ? mmss(e.segundos_abierta)+' / 07:00' : '—'}</span></div>
        <div class="track">
          <div class="fill" style="width:${pct}%;background:${COLOR[n]}"></div>
          <span class="tick" style="left:${UMBRAL_WARN/UMBRAL_CRIT*100}%"></span>
          <span class="tick" style="left:${UMBRAL_SER/UMBRAL_CRIT*100}%"></span>
        </div>
      </div>
        <div class="foot" style="flex-direction: column; align-items: stretch; gap: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-end; width: 100%;">
          <div style="display:flex;gap:22px">
            <div class="kv">Aperturas hoy<b>${e.aperturas_hoy}</b></div>
            <div class="kv">Min. abierta<b>${e.minutos_hoy.toFixed(1)}</b></div>
          </div>
          <div class="sparkwrap">
            <div class="spark">${(e.historial_aperturas || []).map(h=>{
              const c = h>=UMBRAL_CRIT?'var(--crit)':h>=UMBRAL_SER?'var(--serious)':h>=UMBRAL_WARN?'var(--warn)':'#3a3a37';
              return `<div style="height:${Math.max(4,h/maxh*30)}px;background:${c}" title="${mmss(h)}"></div>`;
            }).join('')}</div>
            <small>últimas aperturas</small>
          </div>
        </div>
        ${e.id === 'PSP-01' ? '<button class="btn" onclick="lanzarModelo(this)" style="background:#3987e5; border-color:#3987e5; color:white; font-weight:600; width:100%; padding: 10px;">▶ INICIAR CÁMARA YOLO</button>' : ''}
      </div>
    </div>
    <div class="ghost">⚠ Cámara sin señal — verificar PoE</div>
  </article>`;
}

function ordenar(a,b){
  const r={crit:0,serious:1,warn:2,open:3,ok:4};
  return r[nivel(a)]-r[nivel(b)] || b.segundos_abierta - a.segundos_abierta;
}

function render(){
  const f = document.querySelector('#filtro button[aria-pressed="true"]')?.dataset.f || 'all';
  const lista = [...estado].sort(ordenar).filter(e=>
    f==='all' ? true : f==='open' ? e.abierta : nivel(e)==='crit'||nivel(e)==='serious');

  grid.innerHTML = lista.map(cardHTML).join('');

  estado.forEach(e=>{
      if(e.offline){
          const c = grid.querySelector(`[data-id="${e.id}"]`);
          if(c) c.classList.add('offline');
      }
  });
  resumen();
}

function resumen(){
  const abiertas = estado.filter(e=>e.abierta).length;
  const crit = estado.filter(e=>['crit','serious'].includes(nivel(e))).length;
  const minTotales = estado.reduce((a,e)=>a + (e.minutos_hoy || 0), 0);

  document.getElementById('s-closed').textContent = estado.length - abiertas;
  document.getElementById('s-open').textContent = abiertas;
  document.getElementById('s-crit').textContent = crit;
  document.getElementById('s-total').textContent = minTotales.toFixed(0);

  const ab = document.getElementById('alertbar');
  const peores = estado.filter(e => nivel(e) === 'crit' && Date.now() > (e.ack || 0));

  if(peores.length){
    ab.classList.add('on');
    const p = peores.sort((a,b) => b.segundos_abierta - a.segundos_abierta)[0];
    document.getElementById('alerttxt').innerHTML =
      `${p.nombre} lleva <b>${mmss(p.segundos_abierta)}</b> con la puerta abierta <span>· umbral 07:00 · ${p.zona}</span>`+
      (peores.length>1 ? ` <span>+ ${peores.length-1} puerta(s) más en falta</span>` : '');
  } else {
      ab.classList.remove('on');
  }
}

/* ==== Reloj Local ==== */
function pintarReloj(){
  const d=new Date();
  document.getElementById('clock').textContent=d.toLocaleTimeString('es-CL',{hour12:false});
  document.getElementById('today').textContent=d.toLocaleDateString('es-CL',{weekday:'long',day:'numeric',month:'long'});
}

/* ==== Interacciones ==== */
function ackAll(){
    estado.forEach(e => e.ack = Date.now() + 300000); // silenciar 5 minutos
    resumen();
}

function radio(){ alert('Prototipo: aquí se dispararía el aviso al HT del supervisor de turno o mensaje al grupo de WhatsApp de operaciones.'); }

document.getElementById('filtro').addEventListener('click', ev => {
  const b = ev.target.closest('button');
  if(!b) return;
  ev.currentTarget.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x===b));
  render();
});

/* ==== Ejecución de Modelo YOLO ==== */
function lanzarModelo(btn) {
  const textoOriginal = btn.innerHTML;
  btn.innerHTML = '⏳ Iniciando modelo...';
  btn.style.background = 'var(--surface-2)';
  btn.disabled = true;

  fetch('/api/ejecutar-modelo/')
    .then(response => response.json())
    .then(data => {
      if(data.status === 'ok') {
          btn.innerHTML = '✅ MODELO EN EJECUCIÓN';
          btn.style.background = 'var(--good)';
          btn.style.borderColor = 'var(--good)';
      } else {
          alert("Hubo un error al ejecutar el script: " + data.message);
          btn.innerHTML = textoOriginal;
          btn.style.background = '#3987e5';
          btn.disabled = false;
      }
    })
    .catch(error => {
      console.error('Error de red:', error);
      btn.innerHTML = textoOriginal;
      btn.style.background = '#3987e5';
      btn.disabled = false;
    });
}

/* ==== Inicialización ==== */
pintarReloj();
fetchDatosBackend();

// Actualizar reloj cada segundo
setInterval(pintarReloj, 1000);
// Consultar la API cada 5 segundos (Polling)
setInterval(fetchDatosBackend, 5000);
