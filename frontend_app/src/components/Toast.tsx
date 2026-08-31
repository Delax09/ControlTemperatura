export default function Toast({ mensaje }: { mensaje: string | null }) {
  return <div className={`toast${mensaje ? ' on' : ''}`}>{mensaje}</div>
}
