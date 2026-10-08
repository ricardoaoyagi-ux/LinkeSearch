/** "20261004" -> "04/10/2026" */
export function formatWeek(week: string): string {
  return `${week.slice(6, 8)}/${week.slice(4, 6)}/${week.slice(0, 4)}`;
}

/** Range options in 12h steps from 24h up to (at least) the suggested range. */
export function rangeOptions(suggested: number): number[] {
  const max = Math.max(72, suggested);
  const options: number[] = [];
  for (let h = 24; h <= max; h += 12) options.push(h);
  if (!options.includes(suggested)) options.push(suggested);
  return options.sort((a, b) => a - b);
}
