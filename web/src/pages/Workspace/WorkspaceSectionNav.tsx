import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { WORKSPACE_ROUTES, WORKSPACE_SECTIONS } from '@/lib/workspaceRoutes';

export function WorkspaceSectionNav({ workspaceId }: { workspaceId: string }) {
  return (
    <nav
      aria-label="Workspace sections"
      className="flex gap-1 overflow-x-auto rounded-lg border border-surface-border bg-white p-1"
    >
      {WORKSPACE_SECTIONS.map((section) => (
        <NavLink
          key={section.id}
          to={WORKSPACE_ROUTES.section(workspaceId, section.id)}
          className={({ isActive }) =>
            cn(
              'shrink-0 rounded-md px-3.5 py-2 text-small font-medium transition-colors',
              isActive
                ? 'bg-brand-50 text-brand-700'
                : 'text-ink-muted hover:bg-surface-alt hover:text-ink',
            )
          }
        >
          {section.label}
        </NavLink>
      ))}
    </nav>
  );
}
