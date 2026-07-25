import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { cn } from '@/lib/cn';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';

export interface CommandItem {
  id: string;
  label: string;
  group: string;
  hint?: string;
  keywords?: string[];
  run: () => void;
}

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { setActiveWorkspaceId } = useWorkspace();
  const { workspaces } = useWorkspaceList();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<CommandItem[]>(() => {
    const nav: CommandItem[] = [
      {
        id: 'nav-home',
        label: UI_COPY.homeCrumb,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['home'],
        run: () => navigate(ROUTES.home),
      },
      {
        id: 'nav-workspaces',
        label: UI_COPY.workspacesTitle,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['workspaces', 'list'],
        run: () => navigate(ROUTES.workspaces),
      },
      {
        id: 'nav-documents',
        label: UI_COPY.commandCreateDocuments,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['documents', 'upload', 'create'],
        run: () => navigate(ROUTES.documents),
      },
      {
        id: 'nav-reports',
        label: UI_COPY.commandOpenReports,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['reports'],
        run: () => navigate(ROUTES.reports),
      },
      {
        id: 'nav-report-new',
        label: UI_COPY.createReport,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['create', 'report'],
        run: () => navigate(ROUTES.reportsNew),
      },
      {
        id: 'nav-copilot',
        label: UI_COPY.commandIntelligenceStudio,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['copilot', 'intelligence', 'ai', 'studio'],
        run: () => navigate(ROUTES.copilot),
      },
      {
        id: 'nav-knowledge',
        label: UI_COPY.commandOrganisationalMemory,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['knowledge', 'library', 'memory', 'documents'],
        run: () => navigate(ROUTES.knowledge),
      },
      {
        id: 'nav-search',
        label: UI_COPY.commandSearch,
        group: UI_COPY.commandGroupNavigate,
        keywords: ['search', 'ask'],
        run: () => navigate(ROUTES.knowledge),
      },
    ];

    const switches: CommandItem[] = workspaces.map((workspace) => ({
      id: `ws-${workspace.id}`,
      label: workspace.name,
      group: UI_COPY.commandGroupWorkspaces,
      hint: UI_COPY.commandSwitchWorkspace,
      keywords: ['switch', 'workspace', workspace.name.toLowerCase()],
      run: () => {
        setActiveWorkspaceId(workspace.id);
        navigate(WORKSPACE_ROUTES.section(workspace.id, 'overview'));
      },
    }));

    return [...nav, ...switches];
  }, [navigate, setActiveWorkspaceId, workspaces]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return commands;
    return commands.filter((command) => {
      const haystack = [
        command.label,
        command.group,
        command.hint ?? '',
        ...(command.keywords ?? []),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(normalized);
    });
  }, [commands, query]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActiveIndex(0);
    const timer = window.setTimeout(() => inputRef.current?.focus(), 10);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveIndex((value) =>
          filtered.length === 0 ? 0 : (value + 1) % filtered.length,
        );
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveIndex((value) =>
          filtered.length === 0
            ? 0
            : (value - 1 + filtered.length) % filtered.length,
        );
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        const item = filtered[activeIndex];
        if (item) {
          item.run();
          onClose();
        }
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open, onClose, filtered, activeIndex]);

  if (!open || typeof document === 'undefined') {
    return null;
  }

  const groups = filtered.reduce<Record<string, CommandItem[]>>((acc, item) => {
    acc[item.group] = acc[item.group] ?? [];
    acc[item.group]!.push(item);
    return acc;
  }, {});

  let runningIndex = -1;

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh]">
      <button
        type="button"
        aria-label={UI_COPY.closeCommandPalette}
        className="absolute inset-0 bg-ink/40 animate-backdrop-in"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={UI_COPY.commandPaletteTitle}
        className="relative z-10 w-full max-w-xl overflow-hidden rounded-xl border border-surface-border bg-white shadow-float animate-slide-up"
      >
        <div className="border-b border-surface-border px-3 py-3">
          <Input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={UI_COPY.commandPalettePlaceholder}
            className="h-11 border-0 shadow-none focus-visible:ring-0"
            aria-autocomplete="list"
          />
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-8 text-center text-small text-ink-muted">
              {UI_COPY.commandPaletteEmpty}
            </p>
          ) : (
            Object.entries(groups).map(([group, items]) => (
              <div key={group} className="mb-2">
                <div className="px-3 py-1.5 text-caption uppercase tracking-wide text-ink-faint">
                  {group}
                </div>
                <ul role="listbox">
                  {items.map((item) => {
                    runningIndex += 1;
                    const index = runningIndex;
                    const selected = index === activeIndex;
                    return (
                      <li key={item.id}>
                        <button
                          type="button"
                          role="option"
                          aria-selected={selected}
                          className={cn(
                            'flex w-full items-center justify-between gap-3 rounded-md px-3 py-2.5 text-left text-small transition-colors',
                            selected
                              ? 'bg-brand-50 text-brand-800'
                              : 'text-ink hover:bg-surface-alt',
                          )}
                          onMouseEnter={() => setActiveIndex(index)}
                          onClick={() => {
                            item.run();
                            onClose();
                          }}
                        >
                          <span className="truncate font-medium">{item.label}</span>
                          {item.hint ? (
                            <span className="shrink-0 text-caption text-ink-faint">
                              {item.hint}
                            </span>
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))
          )}
        </div>
        <div className="border-t border-surface-border-light px-4 py-2 text-caption text-ink-faint">
          {UI_COPY.commandPaletteHint}
        </div>
      </div>
    </div>,
    document.body,
  );
}
