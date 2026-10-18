export function parsePage(value: unknown): number | undefined {
  const n = Number(value);
  return Number.isInteger(n) && n > 1 ? n : undefined;
}

