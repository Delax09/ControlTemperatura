/* ==== Miniaturas de cámara (placeholders estáticos) ====
   Aislado del resto de la lógica porque el base64 es muy largo y
   ensucia la búsqueda de funciones en dashboard.js */

const CAM_THUMBS = {
  "anden1": "/static/dashboard/img/anden1.png"
};

function placeholderCam(tipo){
  const g={anden:'#20303f',pasillo:'#2b2e33',congelado:'#1b2a33',tunel:'#161f2b',mp:'#26302a',sala:'#2e2b26'}[tipo]||'#222';
  return `<svg viewBox="0 0 320 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
    <rect width="320" height="180" fill="${g}"/>
    <rect x="0" y="120" width="320" height="60" fill="#000" opacity=".22"/>
    <rect x="196" y="34" width="86" height="112" rx="3" fill="#1d3b6b" opacity=".75"/>
    <rect x="196" y="34" width="86" height="112" rx="3" fill="none" stroke="#3f5f92" stroke-width="2"/>
    ${Array.from({length:9},(_,i)=>`<rect x="198" y="${38+i*12}" width="82" height="4" fill="#7fa8dd" opacity="${0.1+0.06*(i%3)}"/>`).join('')}
    ${Array.from({length:5},(_,i)=>`<rect x="${16+i*30}" y="${96-i*4}" width="26" height="${44+i*4}" rx="2" fill="#3d6fa8" opacity=".55"/>`).join('')}
    <circle cx="46" cy="16" r="7" fill="#111" opacity=".6"/><circle cx="66" cy="16" r="7" fill="#111" opacity=".6"/>
  </svg>`;
}
