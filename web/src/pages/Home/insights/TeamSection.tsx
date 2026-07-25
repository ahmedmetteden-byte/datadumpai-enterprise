import { Collapsible } from '@/components/ui/Collapsible';
import { UI_COPY } from '@/constants/ui';
import { labelForRole } from '@/lib/workspacePermissions';
import type { TeamMember } from '@/types/home';

const statusClass = {
  online: 'bg-success',
  away: 'bg-warning',
  offline: 'bg-ink-faint',
} as const;

export function TeamSection({ team }: { team: TeamMember[] }) {
  return (
    <Collapsible title={UI_COPY.team} defaultOpen={false}>
      <ul className="space-y-2">
        {team.map((member) => (
          <li
            key={member.id}
            className="flex items-center justify-between gap-3 rounded-md px-2 py-2"
          >
            <div className="flex items-center gap-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-small font-semibold text-brand-700">
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
            <span className="inline-flex items-center gap-1.5 text-caption text-ink-muted capitalize">
              <span
                aria-hidden
                className={`h-2 w-2 rounded-full ${statusClass[member.status]}`}
              />
              {member.status}
            </span>
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}
