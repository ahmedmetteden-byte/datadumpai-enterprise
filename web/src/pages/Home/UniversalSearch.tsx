import { useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import type { UniversalSearchPayload } from '@/types/home';

function SuggestionList({
  title,
  items,
}: {
  title: string;
  items: UniversalSearchPayload['recentSearches'];
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
        {title}
      </h3>
      <ul className="space-y-1">
        {items.map((item) => {
          const content = (
            <span className="flex w-full items-center justify-between gap-3 rounded-md px-2.5 py-2 text-small text-ink transition-colors hover:bg-surface-alt">
              <span className="truncate">{item.label}</span>
              {item.meta ? (
                <span className="shrink-0 text-caption text-ink-faint">
                  {item.meta}
                </span>
              ) : null}
            </span>
          );

          return (
            <li key={item.id}>
              {item.href ? (
                <Link to={item.href}>{content}</Link>
              ) : (
                <button type="button" className="w-full text-left">
                  {content}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function UniversalSearch({
  payload,
}: {
  payload: UniversalSearchPayload;
}) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const panelId = useId();
  const blurTimer = useRef<number | null>(null);
  const showPanel = focused;

  return (
    <section className="relative animate-slide-up [animation-delay:60ms]">
      <label htmlFor="universal-search" className="sr-only">
        {UI_COPY.searchPlaceholder}
      </label>
      <div className="relative">
        <span
          aria-hidden
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint"
        >
          ⌕
        </span>
        <Input
          id="universal-search"
          role="combobox"
          aria-expanded={showPanel}
          aria-controls={panelId}
          aria-autocomplete="list"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => {
            if (blurTimer.current) {
              window.clearTimeout(blurTimer.current);
            }
            setFocused(true);
          }}
          onBlur={() => {
            blurTimer.current = window.setTimeout(() => setFocused(false), 120);
          }}
          placeholder={UI_COPY.searchPlaceholder}
          className="h-14 rounded-xl border-surface-border pl-11 text-body shadow-card"
        />
      </div>

      <div
        id={panelId}
        role="listbox"
        hidden={!showPanel}
        className={cn(
          'absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-surface-border bg-white p-4 shadow-float',
          showPanel && 'animate-fade-in',
        )}
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <SuggestionList
            title={UI_COPY.recentSearches}
            items={payload.recentSearches}
          />
          <SuggestionList
            title={UI_COPY.suggestedActions}
            items={payload.suggestedActions}
          />
          <SuggestionList
            title={UI_COPY.recentReports}
            items={payload.recentReports}
          />
          <SuggestionList
            title={UI_COPY.recentWorkspaces}
            items={payload.recentWorkspaces}
          />
        </div>
        <p className="mt-4 border-t border-surface-border-light pt-3 text-caption text-ink-faint">
          {UI_COPY.searchPlaceholderNote}
        </p>
      </div>
    </section>
  );
}
