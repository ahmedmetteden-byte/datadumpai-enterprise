import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { ACTIVE_WORKSPACE_STORAGE_KEY } from '@/lib/workspacePermissions';

interface WorkspaceContextValue {
  activeWorkspaceId: string | null;
  setActiveWorkspaceId: (id: string | null) => void;
  /** Bump after create / update / archive to refetch lists */
  revision: number;
  bumpRevision: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function readStoredWorkspaceId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredWorkspaceId(id: string | null) {
  try {
    if (id) {
      localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, id);
    } else {
      localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
    }
  } catch {
    // ignore quota / private mode
  }
}

export function WorkspaceProvider({
  children,
  initialWorkspaceId = null,
}: {
  children: ReactNode;
  initialWorkspaceId?: string | null;
}) {
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(
    () => initialWorkspaceId ?? readStoredWorkspaceId(),
  );
  const [revision, setRevision] = useState(0);

  const setActiveWorkspaceId = useCallback((id: string | null) => {
    setActiveWorkspaceIdState(id);
    writeStoredWorkspaceId(id);
  }, []);

  const bumpRevision = useCallback(() => {
    setRevision((value) => value + 1);
  }, []);

  const value = useMemo(
    () => ({
      activeWorkspaceId,
      setActiveWorkspaceId,
      revision,
      bumpRevision,
    }),
    [activeWorkspaceId, setActiveWorkspaceId, revision, bumpRevision],
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return ctx;
}
