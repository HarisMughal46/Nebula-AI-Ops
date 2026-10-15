export function HealthRing({ score }: { score: number | null }) {
  const r = 52, c = 2 * Math.PI * r, s = score ?? 0;
  const color = s >= 75 ? "#22d3ee" : s >= 50 ? "#facc15" : "#f43f5e";
  return (
    <svg width="130" height="130" viewBox="0 0 130 130" className="shrink-0">
      <circle cx="65" cy="65" r={r} stroke="#1e293b" strokeWidth="10" fill="none" />
      <circle cx="65" cy="65" r={r} stroke={color} strokeWidth="10" fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c - (c * s) / 100} transform="rotate(-90 65 65)"
        style={{ transition: "stroke-dashoffset 1s", filter: `drop-shadow(0 0 6px ${color})` }} />
      <text x="65" y="62" textAnchor="middle" fill="#e2e8f0" fontSize="28" fontWeight="600">{score ?? "--"}</text>
      <text x="65" y="84" textAnchor="middle" fill="#94a3b8" fontSize="11">HEALTH</text>
    </svg>
  );
}
