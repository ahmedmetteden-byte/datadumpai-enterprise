import { cn } from '@/lib/cn';

interface SpinnerProps {
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
}

/**
 * Indeterminate loading wheel — for actions with no real progress signal
 * to drive a determinate ProgressRing with (e.g. report generation, a
 * single blocking API call). Sized for inline use next to button text.
 */
export function Spinner({ size = 16, strokeWidth = 2.5, className, label = 'Loading' }: SpinnerProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const arc = circumference * 0.25;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={cn('animate-spin text-current', className)}
      role="status"
      aria-label={label}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={`${arc} ${circumference - arc}`}
        opacity={0.85}
      />
    </svg>
  );
}
