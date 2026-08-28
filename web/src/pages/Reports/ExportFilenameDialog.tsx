import { useEffect, useId, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { UI_COPY } from '@/constants/ui';
import type { ReportExportFormat } from '@/types/reports';

const FORMAT_LABELS: Record<ReportExportFormat, string> = {
  docx: UI_COPY.reportsExportWord,
  pdf: UI_COPY.reportsExportPdf,
  pptx: UI_COPY.reportsExportPptx,
};

export function sanitizeExportFilename(name: string): string {
  return name.replace(/[/\\:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim();
}

export function ExportFilenameDialog({
  format,
  defaultName,
  defaultPreparedBy = '',
  onClose,
  onConfirm,
}: {
  format: ReportExportFormat | null;
  defaultName: string;
  defaultPreparedBy?: string;
  onClose: () => void;
  onConfirm: (filename: string, preparedBy: string) => void;
}) {
  const inputId = useId();
  const preparedById = useId();
  const [name, setName] = useState(() => sanitizeExportFilename(defaultName));
  const [preparedBy, setPreparedBy] = useState(defaultPreparedBy);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (format) {
      setName(sanitizeExportFilename(defaultName));
      setPreparedBy(defaultPreparedBy);
      setError(null);
    }
  }, [format, defaultName, defaultPreparedBy]);

  if (!format) return null;

  const extension = format === 'pptx' ? 'pptx' : format;

  function handleConfirm() {
    const sanitized = sanitizeExportFilename(name);
    if (!sanitized) {
      setError(UI_COPY.reportsExportFilenameEmptyError);
      return;
    }
    onConfirm(`${sanitized}.${extension}`, preparedBy.trim());
  }

  return (
    <Modal
      open={Boolean(format)}
      onClose={onClose}
      title={`${UI_COPY.reportsExportFilenameTitle} — ${FORMAT_LABELS[format]}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {UI_COPY.destinationCancel}
          </Button>
          <Button onClick={handleConfirm}>
            {UI_COPY.reportsExportFilenameDownload}
          </Button>
        </>
      }
    >
      <label className="block" htmlFor={inputId}>
        <span className="mb-1 block text-caption font-medium text-ink-muted">
          {UI_COPY.reportsExportFilenameLabel}
        </span>
        <div className="flex items-center gap-2">
          <Input
            id={inputId}
            autoFocus
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                handleConfirm();
              }
            }}
          />
          <span className="whitespace-nowrap text-small text-ink-faint">
            .{extension}
          </span>
        </div>
      </label>
      {error ? (
        <p className="mt-2 text-small text-danger-600">{error}</p>
      ) : (
        <p className="mt-2 text-small text-ink-faint">
          {UI_COPY.reportsExportFilenameHint} .{extension} file.
        </p>
      )}

      <label className="mt-4 block" htmlFor={preparedById}>
        <span className="mb-1 block text-caption font-medium text-ink-muted">
          {UI_COPY.reportsExportPreparedByLabel}
        </span>
        <Input
          id={preparedById}
          value={preparedBy}
          onChange={(event) => setPreparedBy(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              handleConfirm();
            }
          }}
          placeholder="DataDumpAI"
        />
      </label>
      <p className="mt-2 text-small text-ink-faint">
        {UI_COPY.reportsExportPreparedByHint}
      </p>
    </Modal>
  );
}
