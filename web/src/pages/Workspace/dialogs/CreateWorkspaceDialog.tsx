import { useState } from 'react';
import { services } from '@/api/services';
import { Button, Input, Modal } from '@/components/ui';
import { UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import type { CreateWorkspaceInput } from '@/types/workspace';

export function CreateWorkspaceDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (workspaceId: string) => void;
}) {
  const { bumpRevision } = useWorkspace();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    const input: CreateWorkspaceInput = {
      name: name.trim(),
      description: description.trim() || undefined,
    };
    if (!input.name) {
      setError(UI_COPY.nameRequired);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const created = await services.workspace.createWorkspace(input);
      bumpRevision();
      setName('');
      setDescription('');
      onCreated(created.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.createError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={UI_COPY.createWorkspaceTitle}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            {UI_COPY.cancel}
          </Button>
          <Button onClick={() => void handleSubmit()} disabled={submitting}>
            {UI_COPY.createWorkspace}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-small text-ink-muted">
        {UI_COPY.createWorkspaceBody}
      </p>
      <label className="mb-1 block text-caption text-ink-muted" htmlFor="ws-name">
        {UI_COPY.workspaceName}
      </label>
      <Input
        id="ws-name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        autoFocus
        className="mb-4"
      />
      <label
        className="mb-1 block text-caption text-ink-muted"
        htmlFor="ws-description"
      >
        {UI_COPY.workspaceDescription}
      </label>
      <textarea
        id="ws-description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={3}
        className="w-full rounded-lg border border-surface-border bg-white px-4 py-3 text-body text-ink shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      />
      {error ? <p className="mt-3 text-small text-danger">{error}</p> : null}
    </Modal>
  );
}
