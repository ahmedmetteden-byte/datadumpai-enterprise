import { useState } from 'react';
import { services } from '@/api/services';
import { Button, Modal } from '@/components/ui';
import { UI_COPY } from '@/constants/ui';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';

export function ArchiveWorkspaceDialog({
  open,
  workspaceId,
  workspaceName,
  onClose,
  onArchived,
}: {
  open: boolean;
  workspaceId: string;
  workspaceName: string;
  onClose: () => void;
  onArchived: () => void;
}) {
  const { bumpRevision, setActiveWorkspaceId, activeWorkspaceId } =
    useWorkspace();
  const { accessToken } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleArchive() {
    setSubmitting(true);
    setError(null);
    try {
      await services.workspace.archiveWorkspace(workspaceId, { accessToken });
      if (activeWorkspaceId === workspaceId) {
        setActiveWorkspaceId(null);
      }
      bumpRevision();
      onArchived();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.archiveError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={UI_COPY.archiveConfirmTitle}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            {UI_COPY.cancel}
          </Button>
          <Button
            variant="danger"
            onClick={() => void handleArchive()}
            disabled={submitting}
          >
            {UI_COPY.confirmArchive}
          </Button>
        </>
      }
    >
      <p className="text-small text-ink-muted">
        <span className="font-medium text-ink">{workspaceName}</span>
        {' — '}
        {UI_COPY.archiveConfirmBody}
      </p>
      {error ? <p className="mt-3 text-small text-danger">{error}</p> : null}
    </Modal>
  );
}
