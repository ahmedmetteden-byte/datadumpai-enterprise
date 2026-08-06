import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';

const CREATE_NEW_VALUE = '__create_new__';

export function WorkspaceSwitcher({ className }: { className?: string }) {
  const { accessToken } = useAuth();
  const { activeWorkspaceId, setActiveWorkspaceId, bumpRevision } =
    useWorkspace();
  const { workspaces, loading } = useWorkspaceList();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const value =
    activeWorkspaceId && workspaces.some((item) => item.id === activeWorkspaceId)
      ? activeWorkspaceId
      : (workspaces[0]?.id ?? '');

  async function handleCreate() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const created = await services.workspace.createWorkspace(
        { name: name.trim() },
        { accessToken },
      );
      bumpRevision();
      setActiveWorkspaceId(created.id);
      setCreating(false);
      setName('');
    } catch {
      /* keep the form open so the user can retry */
    } finally {
      setBusy(false);
    }
  }

  if (creating) {
    return (
      <div className={className ? `${className} flex items-center gap-2` : 'flex items-center gap-2'}>
        <Input
          autoFocus
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') void handleCreate();
            if (event.key === 'Escape') setCreating(false);
          }}
          placeholder={UI_COPY.createWorkspaceTitle}
          className="h-10 min-w-[10.5rem] max-w-[14rem]"
        />
        <Button size="sm" disabled={busy || !name.trim()} onClick={() => void handleCreate()}>
          {UI_COPY.createWorkspace}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setCreating(false)}>
          {UI_COPY.cancel}
        </Button>
      </div>
    );
  }

  if (loading && workspaces.length === 0) {
    return (
      <div className="h-10 min-w-[10rem] animate-pulse rounded-md bg-surface-border/60" />
    );
  }

  return (
    <div className={className}>
      <label className="sr-only" htmlFor="global-workspace-switcher">
        {UI_COPY.workspaceSelector}
      </label>
      <Select
        id="global-workspace-switcher"
        value={value}
        onChange={(event) => {
          if (event.target.value === CREATE_NEW_VALUE) {
            setCreating(true);
            return;
          }
          setActiveWorkspaceId(event.target.value);
        }}
        className="min-w-[10.5rem] max-w-[14rem] truncate bg-white"
        aria-label={UI_COPY.workspaceSelector}
      >
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
        <option value={CREATE_NEW_VALUE}>+ {UI_COPY.createWorkspace}</option>
      </Select>
    </div>
  );
}
