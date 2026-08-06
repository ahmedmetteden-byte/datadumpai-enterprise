import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { InlineRequestStatus } from '@/components/feedback';
import { GENERAL_WORKSPACE_NAME } from '@/hooks/useEnsureWorkspace';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import type { Project } from '@/types/api';

export type WorkspaceDestination =
  | { type: 'existing'; workspaceId: string }
  | { type: 'new'; name: string }
  | { type: 'temporary' };

type DestinationMode = 'existing' | 'new' | 'temporary';

export function WorkspaceDestinationDialog({
  open,
  onClose,
  workspaces,
  activeWorkspaceId,
  fileCount,
  submitting,
  error,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  workspaces: Project[];
  activeWorkspaceId: string | null;
  fileCount: number;
  submitting: boolean;
  error: string | null;
  onConfirm: (destination: WorkspaceDestination) => void;
}) {
  const [mode, setMode] = useState<DestinationMode>('existing');
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('');
  const [newName, setNewName] = useState('');

  useEffect(() => {
    if (!open) return;
    const hasWorkspaces = workspaces.length > 0;
    setMode(hasWorkspaces ? 'existing' : 'new');
    setSelectedWorkspaceId(
      (activeWorkspaceId && workspaces.some((item) => item.id === activeWorkspaceId)
        ? activeWorkspaceId
        : workspaces[0]?.id) ?? '',
    );
    setNewName('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const canConfirm =
    mode === 'existing'
      ? Boolean(selectedWorkspaceId)
      : mode === 'new'
        ? newName.trim().length > 0
        : true;

  function handleConfirm() {
    if (!canConfirm) return;
    if (mode === 'existing') {
      onConfirm({ type: 'existing', workspaceId: selectedWorkspaceId });
    } else if (mode === 'new') {
      onConfirm({ type: 'new', name: newName.trim() });
    } else {
      onConfirm({ type: 'temporary' });
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={UI_COPY.destinationTitle}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            {UI_COPY.destinationCancel}
          </Button>
          <Button onClick={handleConfirm} disabled={!canConfirm || submitting}>
            {submitting
              ? UI_COPY.destinationConfirming
              : UI_COPY.destinationConfirm}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-small text-ink-muted">
        {fileCount > 1
          ? UI_COPY.destinationBodyPlural.replace('{count}', String(fileCount))
          : UI_COPY.destinationBody}
      </p>

      <div className="space-y-3 text-left">
        {workspaces.length > 0 ? (
          <label
            className={cn(
              'flex cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-colors',
              mode === 'existing'
                ? 'border-brand-500 bg-brand-50/60'
                : 'border-surface-border',
            )}
          >
            <span className="flex items-center gap-2 text-small font-medium text-ink">
              <input
                type="radio"
                name="destination-mode"
                checked={mode === 'existing'}
                onChange={() => setMode('existing')}
                className="h-3.5 w-3.5 text-brand-500 focus:ring-brand-500"
              />
              {UI_COPY.destinationExisting}
            </span>
            {mode === 'existing' ? (
              <Select
                value={selectedWorkspaceId}
                onChange={(event) => setSelectedWorkspaceId(event.target.value)}
                className="w-full"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </Select>
            ) : null}
          </label>
        ) : null}

        <label
          className={cn(
            'flex cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-colors',
            mode === 'new' ? 'border-brand-500 bg-brand-50/60' : 'border-surface-border',
          )}
        >
          <span className="flex items-center gap-2 text-small font-medium text-ink">
            <input
              type="radio"
              name="destination-mode"
              checked={mode === 'new'}
              onChange={() => setMode('new')}
              className="h-3.5 w-3.5 text-brand-500 focus:ring-brand-500"
            />
            {UI_COPY.destinationNew}
          </span>
          {mode === 'new' ? (
            <Input
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder={UI_COPY.destinationNewPlaceholder}
              autoFocus
            />
          ) : null}
        </label>

        <label
          className={cn(
            'flex cursor-pointer flex-col gap-1 rounded-lg border p-3 transition-colors',
            mode === 'temporary'
              ? 'border-brand-500 bg-brand-50/60'
              : 'border-surface-border',
          )}
        >
          <span className="flex items-center gap-2 text-small font-medium text-ink">
            <input
              type="radio"
              name="destination-mode"
              checked={mode === 'temporary'}
              onChange={() => setMode('temporary')}
              className="h-3.5 w-3.5 text-brand-500 focus:ring-brand-500"
            />
            {UI_COPY.destinationTemporary}
          </span>
          <span className="pl-6 text-caption text-ink-faint">
            {UI_COPY.destinationTemporaryHint.replace(
              '{name}',
              GENERAL_WORKSPACE_NAME,
            )}
          </span>
        </label>
      </div>

      {error ? (
        <InlineRequestStatus className="mt-3" kind="error" message={error} />
      ) : null}
    </Modal>
  );
}
