export function StatMeter({
  label,
  value,
  max,
}: {
  label: string
  value: number
  max: number
}) {
  const ratio = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0

  return (
    <div className="play-stat">
      <div className="play-stat-header">
        <span>{label}</span>
        <span>
          {value}/{max}
        </span>
      </div>
      <div className="play-meter-track">
        <div className="play-meter-fill" style={{ width: `${ratio}%` }} />
      </div>
    </div>
  )
}
