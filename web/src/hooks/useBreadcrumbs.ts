import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import type { BreadcrumbItem } from '@/components/ui/Breadcrumbs';
import { ROUTES, UI_COPY } from '@/constants/ui';

export function useBreadcrumbs(): BreadcrumbItem[] {
  const location = useLocation();

  return useMemo(() => {
    if (location.pathname.startsWith(ROUTES.library)) {
      return [{ label: UI_COPY.knowledgeLibrary }];
    }
    return [{ label: UI_COPY.homeCrumb }];
  }, [location.pathname]);
}
