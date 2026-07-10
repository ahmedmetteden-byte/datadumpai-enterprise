import Link from "next/link";
import { DOC_SECTIONS } from "@/lib/content";

const linkBase =
  "block rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500";

export function DocSidebar({ activeSlug }: { activeSlug: string }) {
  return (
    <aside className="w-full shrink-0 lg:w-64" aria-label="Documentation sidebar">
      <nav className="sticky top-24 space-y-6" aria-label="Documentation topics">
        {DOC_SECTIONS.map((section) => (
          <div key={section.slug}>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              {section.title}
            </h2>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const isActive = activeSlug === item.slug;
                return (
                  <li key={item.slug}>
                    <Link
                      href={`/documentation/${item.slug}`}
                      className={
                        isActive
                          ? `${linkBase} bg-brand-50 font-medium text-brand-700`
                          : `${linkBase} text-ink-muted hover:bg-surface-muted hover:text-ink`
                      }
                      aria-current={isActive ? "page" : undefined}
                    >
                      {item.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
