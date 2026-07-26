import type { IsoDateTime } from '@/types/api';

export function formatRelativeTime(value: IsoDateTime, now = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const diffMs = now.getTime() - date.getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() === now.getFullYear() ? undefined : 'numeric',
  });
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatNumber(value: number): string {
  try {
    return new Intl.NumberFormat(undefined).format(value);
  } catch {
    return String(value);
  }
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}% confidence`;
}

export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}
