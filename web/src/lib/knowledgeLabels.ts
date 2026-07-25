import type {
  KnowledgeEntityType,
  KnowledgeProcessingStatusValue,
} from '@/types/knowledge';

export const KNOWLEDGE_TYPE_LABELS: Record<KnowledgeEntityType, string> = {
  document: 'Documents',
  meeting: 'Meetings',
  report: 'Reports',
  policy: 'Policies',
  project: 'Projects',
  decision: 'Decisions',
  action_item: 'Action Items',
};

export const KNOWLEDGE_TYPE_SINGULAR: Record<KnowledgeEntityType, string> = {
  document: 'Document',
  meeting: 'Meeting',
  report: 'Report',
  policy: 'Policy',
  project: 'Project',
  decision: 'Decision',
  action_item: 'Action Item',
};

export const PROCESSING_STATUS_LABELS: Record<
  KnowledgeProcessingStatusValue,
  string
> = {
  uploaded: 'Uploaded',
  extracting: 'Extracting',
  processing: 'Processing',
  indexed: 'Indexed',
  linked: 'Linked',
  verified: 'Verified',
  archived: 'Archived',
  failed: 'Failed',
};

export function formatKnowledgeDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatKnowledgeDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
