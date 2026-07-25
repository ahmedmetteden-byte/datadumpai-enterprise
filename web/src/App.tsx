import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { HomePage } from '@/pages/Home';
import { IntelligenceStudioPage } from '@/pages/IntelligenceStudio';
import { KnowledgePage } from '@/pages/Knowledge';
import { WorkspaceListPage, WorkspacePage } from '@/pages/Workspace';

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="rounded-xl border border-dashed border-surface-border bg-white/70 px-6 py-16 text-center">
      <h1 className="text-page-title text-ink">{title}</h1>
      <p className="mx-auto mt-2 max-w-md text-small text-ink-muted">
        {UI_COPY.comingSoon}
      </p>
    </div>
  );
}

export default function App() {
  return (
    <WorkspaceProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to={ROUTES.home} replace />} />
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.workspaces} element={<WorkspaceListPage />} />
          <Route
            path={`${ROUTES.workspaces}/:workspaceId/*`}
            element={<WorkspacePage />}
          />
          <Route
            path={ROUTES.documents}
            element={<PlaceholderPage title="AI Workspace" />}
          />
          <Route
            path={ROUTES.library}
            element={<Navigate to={ROUTES.knowledge} replace />}
          />
          <Route
            path="/memory"
            element={<Navigate to={ROUTES.knowledge} replace />}
          />
          <Route path={ROUTES.knowledge} element={<KnowledgePage />} />
          <Route
            path={`${ROUTES.knowledge}/:id`}
            element={<KnowledgePage />}
          />
          <Route
            path={ROUTES.reports}
            element={<PlaceholderPage title="Reports" />}
          />
          <Route
            path={ROUTES.reportsNew}
            element={<PlaceholderPage title="Create Report" />}
          />
          <Route path={ROUTES.copilot} element={<IntelligenceStudioPage />} />
          <Route
            path={ROUTES.settings}
            element={<PlaceholderPage title="Settings" />}
          />
          <Route
            path={ROUTES.account}
            element={<PlaceholderPage title="Account" />}
          />
          <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
        </Routes>
      </AppShell>
    </WorkspaceProvider>
  );
}
