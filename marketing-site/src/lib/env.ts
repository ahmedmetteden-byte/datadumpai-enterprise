/** Normalize public env URLs — strip trailing slashes for canonical/OG consistency. */
export function normalizeUrl(value: string | undefined, fallback: string): string {
  const raw = (value ?? fallback).trim();
  return raw.replace(/\/+$/, "");
}
