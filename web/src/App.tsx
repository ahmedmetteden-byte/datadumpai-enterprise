import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import {
  ProtectedRoute,
  PublicOnlyRoute,
} from '@/components/auth/ProtectedRoute';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ROUTES } from '@/constants/ui';
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
} from '@/pages/Auth';
import { HomePage } from '@/pages/Home';
import { KnowledgePage } from '@/pages/Knowledge';
import { BillingPage, BillingReturnPage } from '@/pages/Billing';

function ProtectedApp() {
  return (
    <ProtectedRoute>
      <WorkspaceProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<Navigate to={ROUTES.home} replace />} />
            <Route path={ROUTES.home} element={<HomePage />} />
            <Route path={ROUTES.library} element={<KnowledgePage />} />
            <Route
              path={`${ROUTES.library}/:id`}
              element={<KnowledgePage />}
            />
            <Route path={ROUTES.billing} element={<BillingPage />} />
            <Route path={ROUTES.billingReturn} element={<BillingReturnPage />} />
            <Route
              path="/memory"
              element={<Navigate to={ROUTES.library} replace />}
            />
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
