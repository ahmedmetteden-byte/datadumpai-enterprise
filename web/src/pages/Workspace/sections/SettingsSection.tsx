import { useEffect, useState } from 'react';
import { services } from '@/api/services';
import { InlineRequestStatus } from '@/components/feedback';
import { Button, Input } from '@/components/ui';
import { UI_COPY } from '@/constants/ui';
import { useAuth } from '@/context/AuthContext';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import type { Project } from '@/types/api';
import type { WorkspaceCapabilities } from '@/types/workspace';
import { ArchiveWorkspaceDialog } from '../dialogs/ArchiveWorkspaceDialog';

export function SettingsSection({
  workspace,
  capabilities,
  onArchived,
}: {
  workspace: Project;
  capabilities: WorkspaceCapabilities;
  onArchived: () => void;
}) {
  const { bumpRevision } = useWorkspace();
  const { accessToken } = useAuth();
  const feedback = useRequestFeedback();
  const archiveDialog = useDisclosure(false);
  const [name, setName] = useState(workspace.name);
  const [description, setDescription] = useState(workspace.description);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setName(workspace.name);
    setDescription(workspace.description);
  }, [workspace.id, workspace.name, workspace.description]);

  const canEdit = capabilities.canEditSettings;
  const dirty =
    name.trim() !== workspace.name ||
    description.trim() !== workspace.description;

  async function handleSave() {
    if (!canEdit || !name.trim()) {
      setError(UI_COPY.nameRequired);
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await feedback.run(
        () =>
          services.workspace.updateWorkspace(
            workspace.id,
            {
              name: name.trim(),
              description: description.trim(),
            },
            { accessToken },
          ),
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.settingsSaved,
          // No static `error` override — feedback.run() falls back to
          // err.message, the backend's actual detail, instead of a generic
          // message that hides why the save failed (and disagrees with the
          // inline status below, which already shows the real message).
        },
      );
      bumpRevision();
      setMessage(UI_COPY.settingsSaved);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.settingsSaveError);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        `Permanently delete workspace "${workspace.name}"? This cannot be undone.`,
      )
    ) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await feedback.run(
        () => services.workspace.deleteWorkspace(workspace.id, { accessToken }),
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.requestSuccess,
          // No static `error` override — feedback.run() falls back to
          // err.message, the backend's actual detail, instead of a generic
          // message that hides why deletion failed (and disagrees with the
          // inline status below, which already shows the real message).
        },
      );
      bumpRevision();
      onArchived();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : UI_COPY.deleteWorkspaceError,
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="animate-slide-up space-y-6">
      <section className="rounded-xl border border-surface-border bg-white p-6 sm:p-8">
        <h2 className="text-section text-ink">{UI_COPY.workspaceSettings}</h2>
        <p className="mt-1 text-small text-ink-muted">{UI_COPY.retentionHint}</p>

        <div className="mt-6 max-w-xl space-y-4">
          <div>
            <label
              htmlFor="settings-name"
              className="mb-1 block text-caption text-ink-muted"
            >
              {UI_COPY.workspaceName}
            </label>
            <Input
              id="settings-name"
              value={name}
              disabled={!canEdit}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div>
            <label
              htmlFor="settings-description"
              className="mb-1 block text-caption text-ink-muted"
            >
              {UI_COPY.workspaceDescription}
            </label>
            <textarea
              id="settings-description"
              value={description}
              disabled={!canEdit}
              rows={4}
              onChange={(event) => setDescription(event.target.value)}
              className="w-full rounded-lg border border-surface-border bg-white px-4 py-3 text-body text-ink shadow-sm disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            />
          </div>

          {canEdit ? (
            <Button
              onClick={() => void handleSave()}
              disabled={saving || !dirty}
            >
              {saving ? UI_COPY.requestLoading : UI_COPY.saveChanges}
            </Button>
          ) : null}

          {saving ? (
            <InlineRequestStatus kind="loading" />
          ) : message ? (
            <InlineRequestStatus kind="success" message={message} />
          ) : error ? (
            <InlineRequestStatus
              kind="error"
              message={error}
              onRetry={() => void handleSave()}
            />
          ) : null}
        </div>
      </section>

      {capabilities.canArchive ? (
        <section className="rounded-xl border border-danger/20 bg-white p-6 sm:p-8">
          <h3 className="text-card text-danger">{UI_COPY.dangerZone}</h3>
          <p className="mt-2 max-w-xl text-small text-ink-muted">
            {UI_COPY.archiveConfirmBody}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="danger" onClick={archiveDialog.open}>
              {UI_COPY.archiveWorkspace}
            </Button>
            <Button
              variant="danger"
              onClick={() => void handleDelete()}
              disabled={deleting}
            >
              {deleting ? UI_COPY.requestLoading : UI_COPY.deleteWorkspace}
            </Button>
          </div>
        </section>
      ) : null}

      <ArchiveWorkspaceDialog
        open={archiveDialog.isOpen}
        onClose={archiveDialog.close}
        workspaceId={workspace.id}
        workspaceName={workspace.name}
        onArchived={onArchived}
      />
    </div>
  );
}
