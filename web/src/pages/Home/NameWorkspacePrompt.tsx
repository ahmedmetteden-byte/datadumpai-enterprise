import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { DEFAULT_WORKSPACE_NAME } from '@/hooks/useEnsureWorkspace';
import { UI_COPY } from '@/constants/ui';

export function NameWorkspacePrompt({ workspaceId }: { workspaceId: string }) {
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const { bumpRevision } = useWorkspace();
  const { workspaces } = useWorkspaceList();
  const [dismissed, setDismissed] = useState(false);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  const workspace = workspaces.find((item) => item.id === workspaceId);

  if (dismissed || !workspace || workspace.name !== DEFAULT_WORKSPACE_NAME) {
    return null;
  }

  async function handleSave() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await services.workspace.updateWorkspace(
        workspaceId,
        { name: name.trim() },
        auth,
      );
      bumpRevision();
      setDismissed(true);
    } catch {
      /* leave the form open so the user can retry */
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 sm:p-5">
      <h3 className="text-card text-ink">{UI_COPY.nameWorkspaceTitle}</h3>
      <p className="mt-1 text-small text-ink-muted">
        {UI_COPY.nameWorkspaceBody}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') void handleSave();
          }}
          placeholder={UI_COPY.nameWorkspacePlaceholder}
          className="min-w-[14rem] flex-1"
        />
        <Button
          size="sm"
          disabled={saving || !name.trim()}
          onClick={() => void handleSave()}
        >
          {UI_COPY.nameWorkspaceSave}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
          {UI_COPY.nameWorkspaceDismiss}
        </Button>
      </div>
    </div>
  );
}
