import type { ReasoningMode } from '@/types/intelligence';

export const REASONING_MODES: Array<{
  id: ReasoningMode;
  label: string;
  placeholder: string;
}> = [
  {
    id: 'ask',
    label: 'Ask',
    placeholder: 'Ask anything about your workspace…',
  },
  {
    id: 'summarise',
    label: 'Summarise',
    placeholder: 'What should I summarise from this workspace?',
  },
  {
    id: 'compare',
    label: 'Compare',
    placeholder: 'Which reports, meetings, or periods should I compare?',
  },
  {
    id: 'analyse',
    label: 'Analyse',
    placeholder: 'What should I analyse in the workspace knowledge?',
  },
  {
    id: 'generate_report',
    label: 'Generate Report',
    placeholder: 'Describe the report you want outlined from this workspace…',
  },
  {
    id: 'recommend',
    label: 'Recommend',
    placeholder: 'What decision or outcome should I recommend next steps for?',
  },
];

export function placeholderForMode(mode: ReasoningMode): string {
  return (
    REASONING_MODES.find((item) => item.id === mode)?.placeholder ??
    REASONING_MODES[0]!.placeholder
  );
}

export function greetingForNow(date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning.';
  if (hour < 18) return 'Good afternoon.';
  return 'Good evening.';
}
