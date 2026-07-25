import { EmptyState } from '@/components/ui/EmptyState';
import { UI_COPY } from '@/constants/ui';

export function EmptyKnowledge({
  variant,
  onUpload,
  onClearSearch,
}: {
  variant: 'none' | 'search' | 'uploads' | 'relationships';
  onUpload?: () => void;
  onClearSearch?: () => void;
}) {
  if (variant === 'search') {
    return (
      <EmptyState
        className="min-h-[40vh] border-0 bg-transparent"
        title={UI_COPY.knowledgeEmptySearchTitle}
        description={UI_COPY.knowledgeEmptySearchDescription}
        actionLabel={UI_COPY.knowledgeClearSearch}
        onAction={onClearSearch}
        icon="⌕"
      />
    );
  }
  if (variant === 'uploads') {
    return (
      <EmptyState
        className="border-0 bg-transparent py-8"
        title={UI_COPY.knowledgeEmptyUploadsTitle}
        description={UI_COPY.knowledgeEmptyUploadsDescription}
        actionLabel={UI_COPY.knowledgeUpload}
        onAction={onUpload}
        icon="↑"
      />
    );
  }
  if (variant === 'relationships') {
    return (
      <EmptyState
        className="border-0 bg-transparent py-6"
        title={UI_COPY.knowledgeEmptyRelationshipsTitle}
        description={UI_COPY.knowledgeEmptyRelationshipsDescription}
        icon="⧉"
      />
    );
  }
  return (
    <EmptyState
      className="min-h-[40vh] border-0 bg-transparent"
      title={UI_COPY.knowledgeEmptyTitle}
      description={UI_COPY.knowledgeEmptyDescription}
      actionLabel={UI_COPY.knowledgeUpload}
      onAction={onUpload}
      icon="◎"
    />
  );
}
