import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/cn';

export function ReportMarkdown({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div className={cn('space-y-4 text-body text-ink', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-2 text-page-title text-ink">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-6 border-b border-surface-border pb-1.5 text-section text-ink first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-1 mt-4 text-card text-ink">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="leading-relaxed text-ink">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-ink">{children}</strong>
          ),
          ul: ({ children }) => (
            <ul className="list-disc space-y-1 pl-5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal space-y-1 pl-5">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-brand-300 pl-3 text-ink-muted">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="border-surface-border" />,
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-brand-600 underline hover:text-brand-700"
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-surface-alt px-1 py-0.5 text-small text-ink">
              {children}
            </code>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-small">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-surface-border bg-surface-alt px-2 py-1.5 text-left font-semibold text-ink">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-surface-border px-2 py-1.5 align-top text-ink">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
