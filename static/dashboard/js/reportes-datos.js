/* ==== Datos simulados del reporte general ====
   TEMPORAL, igual que temp-sim.js: el backend todavía no tiene identidad de
   puerta en EventoPuerta, así que no existe de dónde leer un consolidado por
   cámara. Este módulo genera uno plausible para diseñar la vista.

   Dos decisiones importantes:

   1. La aleatoriedad es DETERMINISTA (PRNG sembrado por puerta + hora). Un
      ranking que se reordena en cada repintado no sirve para nada. Los mismos
      datos salen siempre, y solo cambian al cambiar de hora.

   2. La deriva de temperatura no se sortea: se deriva de los minutos abiertos
      con la misma saturación exponencial que usa temp-sim.js, así que una
      puerta más tiempo abierta siempre calienta más. Ranking y temperatura son
      coherentes entre sí. */

/* Flota de puertas: [id, nombre, zona, set point, tipo, intensidad de uso] */
const FLOTA = [
  ['PSP-01', 'ANDÉN PSP 1',    'Andén despacho · rápida 3 m',   -0.5, 'anden',     1.00],
  ['PSP-02', 'ANDÉN PSP 2',    'Andén recepción · rápida 3 m',  -0.5, 'anden',     0.92],
  ['DES-01', 'DESPACHO SUR',   'Andén sur seccional',            2.0, 'anden',     0.78],
  ['MP-02',  'MATERIA PRIMA 2','Recepción materia prima',        0.0, 'mp',        0.71],
  ['PTT-01', 'PASILLO PTT 1',  'Pasillo pre-túnel',              2.0, 'pasillo',   0.55],
  ['CF-03',  'CÁMARA FRÍO 3',  'PT congelado',                 -18.0, 'congelado', 0.38],
  ['CF-04',  'CÁMARA FRÍO 4',  'PT congelado',                 -18.0, 'congelado', 0.30],
  ['TC-01',  'TÚNEL CONG. 1',  'Túnel de congelado',           -28.0, 'tunel',     0.16],
];

const AMBIENTE_REPORTE = 12;   // °C del pasillo/andén que entra al abrir
const K_DERIVA         = 0.05; // saturación por minuto abierto

/* PRNG determinista (mulberry32) sembrado con un hash de la clave. */
function rngDe(clave){
  let h = 2166136261;
  for(let i = 0; i < clave.length; i++) h = Math.imul(h ^ clave.charCodeAt(i), 16777619);
  let s = h >>> 0;
  return function(){
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* Índice absoluto de hora: estable dentro de la misma hora del reloj. */
const horaAbsoluta = ts => Math.floor(ts / 3600000);

/* Una hora de actividad de una puerta. */
function horaDe(puerta, hAbs){
  const [id, , , setPoint, , intensidad] = puerta;
  const r = rngDe(`${id}-${hAbs}`);

  // La actividad baja de noche (turno reducido).
  const hora = (hAbs % 24 + 24) % 24;
  const factorTurno = (hora >= 7 && hora < 23) ? 1 : 0.28;

  const aperturas = Math.round(r() * 9 * intensidad * factorTurno);
  // Minutos abiertos: cada apertura aporta entre 0,4 y 5 minutos.
  let minutos = 0;
  for(let i = 0; i < aperturas; i++) minutos += 0.4 + r() * 4.6;
  minutos = Math.min(60, minutos);

  // Deriva térmica saturante: coherente con el modelo de temp-sim.js.
  const techo = AMBIENTE_REPORTE - setPoint;
  const deriva = techo * (1 - Math.exp(-K_DERIVA * minutos));

  return {
    hAbs, hora, aperturas,
    minutos: +minutos.toFixed(1),
    deriva:  +Math.max(0, deriva).toFixed(1),
    tempMax: +(setPoint + deriva).toFixed(1),
  };
}

/* Consolidado de una puerta en una ventana de N horas (la más reciente al final). */
function resumenPuerta(puerta, horas, ahora){
  const hAhora = horaAbsoluta(ahora);
  const serie = [];
  for(let k = horas - 1; k >= 0; k--) serie.push(horaDe(puerta, hAhora - k));

  const [id, nombre, zona, setPoint, tipo] = puerta;
  const minutos   = serie.reduce((a, h) => a + h.minutos, 0);
  const aperturas = serie.reduce((a, h) => a + h.aperturas, 0);
  const derivaMax = Math.max(...serie.map(h => h.deriva));
  const horasFuera = serie.filter(h => h.deriva > 1.2).length;

  return {
    id, nombre, zona, setPoint, tipo, serie,
    minutos:   +minutos.toFixed(1),
    aperturas,
    derivaMax: +derivaMax.toFixed(1),
    tempMax:   +(setPoint + derivaMax).toFixed(1),
    horasFuera,
    // Minutos promedio por apertura: indica si el problema es frecuencia o duración.
    minPorApertura: aperturas ? +(minutos / aperturas).toFixed(1) : 0,
  };
}

/* Reporte completo, ordenado por tiempo abierto (el ranking pedido). */
function generarReporte(horas){
  const ahora = Date.now();
  const filas = FLOTA.map(p => resumenPuerta(p, horas, ahora))
                      .sort((a, b) => b.minutos - a.minutos);
  return {
    horas, generado: new Date(ahora), filas,
    totalMinutos:   +filas.reduce((a, f) => a + f.minutos, 0).toFixed(1),
    totalAperturas:  filas.reduce((a, f) => a + f.aperturas, 0),
    peorDeriva:      filas.reduce((m, f) => f.derivaMax > m.derivaMax ? f : m, filas[0]),
    puertasFuera:    filas.filter(f => f.horasFuera > 0).length,
  };
}
