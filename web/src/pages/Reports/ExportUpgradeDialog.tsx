import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { ROUTES, UI_COPY } from '@/constants/ui';
import type { ReportExportFormat } from '@/types/reports';

const FORMAT_LABELS: Record<ReportExportFormat, string> = {
  docx: UI_COPY.reportsExportWord,
  pdf: UI_COPY.reportsExportPdf,
  pptx: UI_COPY.reportsExportPptx,
};

export function ExportUpgradeDialog({
  format,
  requiredPlan,
  onClose,
}: {
  format: ReportExportFormat | null;
  requiredPlan: string | null;
  onClose: () => void;
}) {
  const navigate = useNavigate();

  if (!format || !requiredPlan) return null;

  return (
    <Modal
      open={Boolean(format)}
      onClose={onClose}
      title={UI_COPY.reportsExportLockedTitle}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {UI_COPY.reportsExportLockedDismiss}
          </Button>
          <Button onClick={() => navigate(ROUTES.billing)}>
            {UI_COPY.reportsExportLockedCta}
          </Button>
        </>
      }
    >
      <p className="text-small text-ink-muted">
        {FORMAT_LABELS[format]} export requires the {requiredPlan} plan or
        higher. Upgrade to unlock it for this and every future report.
      </p>
    </Modal>
  );
}
