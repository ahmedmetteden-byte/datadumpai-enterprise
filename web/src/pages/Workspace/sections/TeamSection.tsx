import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { labelForRole } from '@/lib/workspacePermissions';
import type { TeamMember } from '@/types/home';
import type { WorkspaceCapabilities } from '@/types/workspace';

const statusClass = {
  online: 'bg-success',
  away: 'bg-warning',
  offline: 'bg-ink-faint',
} as const;

export function TeamPanelSection({
  team,
  capabilities,
}: {
  team: TeamMember[];
  capabilities: WorkspaceCapabilities;
}) {
  return (
    <section className="animate-slide-up rounded-xl border border-surface-border bg-white p-6 sm:p-8">
      <SectionHeader
        title={UI_COPY.team}
        description={
          capabilities.canManageTeam ? UI_COPY.manageTeamHint : undefined
        }
      />
      {team.length === 0 ? (
        <EmptyState
          className="border-0 bg-surface-alt/50 py-12"
          icon="◎"
          title={UI_COPY.emptyTeamTitle}
          description={UI_COPY.emptyTeamDescription}
        />
      ) : (
        <ul className="divide-y divide-surface-border-light">
          {team.map((member) => (
            <li
              key={member.id}
              className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0 last:pb-0"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-small font-semibold text-brand-700">
                  {member.name
                    .split(' ')
                    .map((part) => part[0])
                    .slice(0, 2)
                    .join('')}
                </span>
                <div>
                  <div className="text-small font-medium text-ink">
                    {member.name}
                  </div>
                  <div className="text-caption text-ink-muted">
                    {member.title ?? labelForRole(member.role)}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone="brand">{labelForRole(member.role)}</Badge>
                <span className="inline-flex items-center gap-1.5 text-caption text-ink-muted capitalize">
                  <span
                    aria-hidden
                    className={`h-2 w-2 rounded-full ${statusClass[member.status]}`}
                  />
                  {member.status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
