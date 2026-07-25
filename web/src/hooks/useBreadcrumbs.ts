import { useMemo } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import type { BreadcrumbItem } from '@/components/ui/Breadcrumbs';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { WORKSPACE_ROUTES, WORKSPACE_SECTIONS } from '@/lib/workspaceRoutes';

const PAGE_CRUMBS: Record<string, string> = {
  [ROUTES.home]: UI_COPY.homeCrumb,
  [ROUTES.workspaces]: UI_COPY.workspacesTitle,
  [ROUTES.documents]: 'AI Workspace',
  [ROUTES.library]: UI_COPY.knowledgeTitle,
  [ROUTES.knowledge]: UI_COPY.knowledgeTitle,
  [ROUTES.reports]: 'Reports',
  [ROUTES.reportsNew]: UI_COPY.createReport,
  [ROUTES.copilot]: 'Intelligence Studio',
  [ROUTES.settings]: 'Settings',
  [ROUTES.account]: 'Account',
};

export function useBreadcrumbs(): BreadcrumbItem[] {
  const location = useLocation();
  const params = useParams<{ workspaceId?: string }>();
  const { workspaces } = useWorkspaceList();

  return useMemo(() => {
    const pathname = location.pathname;
    const items: BreadcrumbItem[] = [
      { label: UI_COPY.homeCrumb, href: ROUTES.home },
    ];

    if (pathname === ROUTES.home) {
      return [{ label: UI_COPY.homeCrumb }];
    }

    const workspaceMatch = pathname.match(
      /^\/workspaces\/([^/]+)(?:\/([^/]+))?/,
    );
    if (workspaceMatch) {
      const workspaceId = workspaceMatch[1] ?? params.workspaceId;
      const sectionId = workspaceMatch[2];
      const workspace = workspaces.find((item) => item.id === workspaceId);

      items.push({
        label: UI_COPY.workspacesTitle,
        href: WORKSPACE_ROUTES.list,
      });

      if (workspaceId) {
        items.push({
          label: workspace?.name ?? UI_COPY.workspaceSelector,
          href: WORKSPACE_ROUTES.section(workspaceId, 'overview'),
        });
      }

      if (sectionId && sectionId !== 'overview') {
        const section = WORKSPACE_SECTIONS.find((item) => item.id === sectionId);
        items.push({ label: section?.label ?? sectionId });
      }

      return items;
    }

    if (pathname === ROUTES.workspaces) {
      items.push({ label: UI_COPY.workspacesTitle });
      return items;
    }

    if (pathname === ROUTES.knowledge || pathname.startsWith(`${ROUTES.knowledge}/`)) {
      items.push({
        label: UI_COPY.knowledgeTitle,
        href:
          pathname === ROUTES.knowledge ? undefined : ROUTES.knowledge,
      });
      if (pathname.startsWith(`${ROUTES.knowledge}/`)) {
        items.push({ label: UI_COPY.knowledgePreview });
      }
      return items;
    }

    const pageLabel = PAGE_CRUMBS[pathname];
    if (pageLabel) {
      items.push({ label: pageLabel });
      return items;
    }

    items.push({ label: pathname.slice(1) || UI_COPY.homeCrumb });
    return items;
  }, [location.pathname, params.workspaceId, workspaces]);
}
