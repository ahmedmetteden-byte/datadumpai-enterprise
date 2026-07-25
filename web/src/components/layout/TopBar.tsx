import { useEffect } from 'react';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { IconButton } from '@/components/ui/IconButton';
import { CommandPalette } from '@/components/layout/CommandPalette';
import { WorkspaceSwitcher } from '@/components/layout/WorkspaceSwitcher';
import { UI_COPY } from '@/constants/ui';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useBreadcrumbs } from '@/hooks/useBreadcrumbs';

export function TopBar({ onOpenMobileNav }: { onOpenMobileNav: () => void }) {
  const breadcrumbs = useBreadcrumbs();
  const { isOpen, open, close, toggle } = useDisclosure(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const isMod = event.metaKey || event.ctrlKey;
      if (isMod && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        toggle();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [toggle]);

  return (
    <>
      <header className="sticky top-0 z-20 border-b border-surface-border/70 bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex max-w-content items-center gap-3 px-4 py-3 sm:px-6 lg:px-10">
          <IconButton
            label={UI_COPY.openMenu}
            onClick={onOpenMobileNav}
            className="lg:hidden"
          >
            <span aria-hidden>☰</span>
          </IconButton>

          <Breadcrumbs items={breadcrumbs} className="min-w-0 flex-1" />

          <div className="ml-auto flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={open}
              className="hidden h-10 items-center gap-2 rounded-md border border-surface-border bg-white px-3 text-small text-ink-muted transition-colors hover:border-brand-200 hover:text-ink sm:inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-label={UI_COPY.openCommandPalette}
            >
              <span>{UI_COPY.commandPaletteTitle}</span>
              <kbd className="rounded border border-surface-border bg-surface-alt px-1.5 py-0.5 text-[10px] font-medium text-ink-faint">
                ⌘K
              </kbd>
            </button>
            <IconButton
              label={UI_COPY.openCommandPalette}
              onClick={open}
              className="sm:hidden"
            >
              <span aria-hidden>⌕</span>
            </IconButton>
            <WorkspaceSwitcher />
          </div>
        </div>
      </header>

      <CommandPalette open={isOpen} onClose={close} />
    </>
  );
}
