import { useLocation, useNavigate } from 'react-router-dom';
import { Select } from '@/components/ui/Select';
import { UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { WORKSPACE_ROUTES, WORKSPACE_SECTIONS } from '@/lib/workspaceRoutes';
import type { WorkspaceSectionId } from '@/types/workspace';

function sectionFromPath(pathname: string): WorkspaceSectionId | null {
  const match = pathname.match(/^\/workspaces\/[^/]+\/([^/]+)/);
  if (!match?.[1]) return null;
  const id = match[1] as WorkspaceSectionId;
  return WORKSPACE_SECTIONS.some((section) => section.id === id) ? id : 'overview';
}

export function WorkspaceSwitcher({ className }: { className?: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspace();
  const { workspaces, loading } = useWorkspaceList();

  const value =
    activeWorkspaceId && workspaces.some((item) => item.id === activeWorkspaceId)
      ? activeWorkspaceId
      : (workspaces[0]?.id ?? '');

  function handleChange(workspaceId: string) {
    setActiveWorkspaceId(workspaceId);
    const section = sectionFromPath(location.pathname);
    if (location.pathname.startsWith('/workspaces/') && section) {
      navigate(WORKSPACE_ROUTES.section(workspaceId, section));
      return;
    }
    if (location.pathname === WORKSPACE_ROUTES.list) {
      navigate(WORKSPACE_ROUTES.section(workspaceId, 'overview'));
    }
  }

  if (loading && workspaces.length === 0) {
    return (
      <div className="h-10 min-w-[10rem] animate-pulse rounded-md bg-surface-border/60" />
    );
  }

  if (workspaces.length === 0) {
    return null;
  }

  return (
    <div className={className}>
      <label className="sr-only" htmlFor="global-workspace-switcher">
        {UI_COPY.workspaceSelector}
      </label>
      <Select
        id="global-workspace-switcher"
        value={value}
        onChange={(event) => handleChange(event.target.value)}
        className="min-w-[10.5rem] max-w-[14rem] truncate bg-white"
        aria-label={UI_COPY.workspaceSelector}
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </Select>
    </div>
  );
}
