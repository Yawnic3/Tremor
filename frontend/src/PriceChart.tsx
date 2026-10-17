import { useEffect, useState } from "react";
type Series = {
  provider: string;
  synthetic: boolean;
  warning: string;
  prices: { date: string; close: number }[];
};
export function PriceChart({
  ticker,
  eventDate,
  demo,
}: {
  ticker: string;
  eventDate: string;
  demo: boolean;
}) {
  const [data, setData] = useState<Series | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    setData(null);
    setError("");
    fetch(`/api/companies/${ticker}/prices?demo=${demo}`, {
      signal: abort.signal,
    })
      .then(async (r) => {
        if (!r.ok) throw Error("Price history unavailable");
        return r.json();
      })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => abort.abort();
  }, [ticker, demo]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading prices…</p>;
  const day = eventDate.slice(0, 10),
    all = data.prices,
    idx = all.findIndex((p) => p.date >= day),
    rows = idx < 0 ? [] : all.slice(Math.max(0, idx - 25), idx + 26);
  if (!rows.length)
    return (
      <p className="empty">{data.warning} No prices covering this event.</p>
    );
  const low = Math.min(...rows.map((p) => p.close)),
    high = Math.max(...rows.map((p) => p.close)),
    range = high - low || 1;
  const x = (i: number) => 10 + (i / (rows.length - 1 || 1)) * 270,
    y = (v: number) => 110 - ((v - low) / range) * 80;
  const eventIdx = rows.findIndex((p) => p.date >= day);
  return (
    <div className="price-chart">
      <div className="section-label">
        <span>{ticker} · DAILY CLOSE</span>
        <b>{data.synthetic ? "SYNTHETIC" : "CACHED"}</b>
      </div>
      <svg
        viewBox="0 0 300 150"
        role="img"
        aria-label={`${ticker} daily closes, event on ${day}. ${data.warning}`}
      >
        <line x1="10" x2="280" y1="110" y2="110" stroke="#dfe7da" />
        <path
          d={rows
            .map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.close)}`)
            .join(" ")}
          fill="none"
          stroke="#4e826c"
          strokeWidth="2"
        />
        <line
          x1={x(eventIdx)}
          x2={x(eventIdx)}
          y1="15"
          y2="117"
          stroke="#bd9671"
          strokeDasharray="3 3"
        />
        <text x={Math.min(220, x(eventIdx) + 4)} y="12">
          Event date
        </text>
        <text x="10" y="140">
          {rows[0].date}
        </text>
        <text x="218" y="140">
          {rows[rows.length - 1].date}
        </text>
        <text x="10" y="22">
          ${high.toFixed(2)}
        </text>
      </svg>
      <p className="muted">
        {data.warning} Source: {data.provider}
      </p>
    </div>
  );
}
