export function percent(value: number | null): string {
  return value === null
    ? "—"
    : `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}
