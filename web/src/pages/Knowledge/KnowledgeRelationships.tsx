import { EmptyKnowledge } from '@/pages/Knowledge/EmptyKnowledge';
import { UI_COPY } from '@/constants/ui';
import { KNOWLEDGE_TYPE_SINGULAR } from '@/lib/knowledgeLabels';
import type { KnowledgeDetail, KnowledgeEntityType, KnowledgeListItem } from '@/types/knowledge';

const RELATED_GROUPS: Array<{
  key: string;
  title: string;
  types: KnowledgeEntityType[];
}> = [
  {
    key: 'meetings',
    title: UI_COPY.knowledgeRelatedMeetings,
    types: ['meeting'],
  },
  {
    key: 'reports',
    title: UI_COPY.knowledgeRelatedReports,
    types: ['report'],
  },
  {
    key: 'decisions',
    title: UI_COPY.knowledgeRelatedDecisions,
    types: ['decision'],
  },
  {
    key: 'policies',
    title: UI_COPY.knowledgeRelatedPolicies,
    types: ['policy'],
  },
  {
    key: 'projects',
    title: UI_COPY.knowledgeRelatedProjects,
    types: ['project'],
  },
];

function RelatedList({
  title,
  items,
  onOpen,
}: {
  title: string;
  items: KnowledgeListItem[];
  onOpen: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-2">
      <h4 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
        {title}
      </h4>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onOpen(item.id)}
              className="w-full rounded-md px-2 py-1.5 text-left text-small text-ink hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <span className="font-medium">{item.title}</span>
              <span className="mt-0.5 block text-caption text-ink-muted">
                {KNOWLEDGE_TYPE_SINGULAR[item.type]}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function KnowledgeRelationships({
  detail,
  onOpen,
}: {
  detail: KnowledgeDetail;
  onOpen: (id: string) => void;
}) {
  const hasAny =
    detail.related.length > 0 || detail.referencedBy.length > 0;

  if (!hasAny) {
    return <EmptyKnowledge variant="relationships" />;
  }

  return (
    <section className="space-y-5" aria-label={UI_COPY.knowledgeRelationships}>
      <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
        {UI_COPY.knowledgeRelationships}
      </h3>

      {RELATED_GROUPS.map((group) => (
        <RelatedList
          key={group.key}
          title={group.title}
          items={detail.related.filter((item) =>
            group.types.includes(item.type),
          )}
          onOpen={onOpen}
        />
      ))}

      <RelatedList
        title={UI_COPY.knowledgeRelatedOther}
        items={detail.related.filter(
          (item) =>
            !RELATED_GROUPS.some((group) => group.types.includes(item.type)),
        )}
        onOpen={onOpen}
      />

      <div className="space-y-2">
        <h4 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          {UI_COPY.knowledgeReferencedBy}
        </h4>
        {detail.referencedBy.length === 0 ? (
          <p className="text-small text-ink-muted">
            {UI_COPY.knowledgeNoReferencedBy}
          </p>
        ) : (
          <ul className="space-y-1.5">
            {detail.referencedBy.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onOpen(item.id)}
                  className="w-full rounded-md px-2 py-1.5 text-left text-small font-medium text-ink hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  {item.title}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2">
        <h4 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          {UI_COPY.knowledgeRelatedKnowledge}
        </h4>
        <ul className="space-y-1">
          {detail.relationships.map((rel) => (
            <li key={rel.id} className="text-small text-ink-muted">
              {rel.label ?? rel.predicate}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
