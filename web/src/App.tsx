import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import {
  ProtectedRoute,
  PublicOnlyRoute,
} from '@/components/auth/ProtectedRoute';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { AccountPage } from '@/pages/Account';
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
} from '@/pages/Auth';
import { HomePage } from '@/pages/Home';
import { IntelligenceStudioPage } from '@/pages/IntelligenceStudio';
import { KnowledgePage } from '@/pages/Knowledge';
import {
  ReportDetailPage,
  ReportGeneratePage,
  ReportsPage,
} from '@/pages/Reports';
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

function ProtectedApp() {
  return (
    <ProtectedRoute>
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
            <Route path={ROUTES.reports} element={<ReportsPage />} />
            <Route path={ROUTES.reportsNew} element={<ReportGeneratePage />} />
            <Route
              path={`${ROUTES.reports}/:reportId`}
              element={<ReportDetailPage />}
            />
            <Route path={ROUTES.copilot} element={<IntelligenceStudioPage />} />
            <Route
              path={ROUTES.settings}
              element={<PlaceholderPage title="Settings" />}
            />
            <Route path={ROUTES.account} element={<AccountPage />} />
            <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
          </Routes>
        </AppShell>
      </WorkspaceProvider>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path={ROUTES.login}
        element={
          <PublicOnlyRoute>
            <LoginPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path={ROUTES.register}
        element={
          <PublicOnlyRoute>
            <RegisterPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path={ROUTES.forgotPassword}
        element={
          <PublicOnlyRoute>
            <ForgotPasswordPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/auth"
        element={<Navigate to={ROUTES.login} replace />}
      />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  );
}
