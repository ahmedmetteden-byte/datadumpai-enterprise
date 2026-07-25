import { Badge } from '@/components/ui/Badge';
import { PROCESSING_STATUS_LABELS } from '@/lib/knowledgeLabels';
import { cn } from '@/lib/cn';
import type { KnowledgeProcessingStatusValue } from '@/types/knowledge';

const TONE: Record<
  KnowledgeProcessingStatusValue,
  'neutral' | 'brand' | 'success' | 'warning'
> = {
  uploaded: 'neutral',
  extracting: 'warning',
  processing: 'warning',
  indexed: 'brand',
  linked: 'brand',
  verified: 'success',
  archived: 'neutral',
  failed: 'warning',
};

export function ProcessingBadge({
  status,
  className,
  pulse,
}: {
  status: KnowledgeProcessingStatusValue;
  className?: string;
  pulse?: boolean;
}) {
  const inFlight = ['uploaded', 'extracting', 'processing'].includes(status);
  return (
    <Badge
      tone={TONE[status]}
      className={cn(
        inFlight || pulse ? 'animate-pulse' : undefined,
        className,
      )}
    >
      {PROCESSING_STATUS_LABELS[status]}
    </Badge>
  );
}
