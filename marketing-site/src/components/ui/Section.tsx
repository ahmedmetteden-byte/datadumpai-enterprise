type SectionProps = {
  children: React.ReactNode;
  className?: string;
  id?: string;
  muted?: boolean;
  "aria-labelledby"?: string;
};

export function Section({
  children,
  className = "",
  id,
  muted,
  "aria-labelledby": ariaLabelledby,
}: SectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={ariaLabelledby}
      className={`py-20 md:py-28 ${muted ? "bg-surface-muted" : ""} ${className}`}
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-8">{children}</div>
    </section>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  centered = true,
  titleId,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  centered?: boolean;
  titleId?: string;
}) {
  return (
    <div className={`mb-14 max-w-3xl ${centered ? "mx-auto text-center" : ""}`}>
      {eyebrow && (
        <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-brand-600">
          {eyebrow}
        </p>
      )}
      <h2
        id={titleId}
        className="text-3xl font-bold tracking-tight text-ink md:text-4xl lg:text-[2.75rem] lg:leading-tight"
      >
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-lg leading-relaxed text-ink-muted">{description}</p>
      )}
    </div>
  );
}

export function PageHero({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  const headingId = "page-hero-heading";

  return (
    <section
      className="relative overflow-hidden bg-mesh-gradient pb-16 pt-12 md:pb-20 md:pt-16"
      aria-labelledby={headingId}
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="max-w-3xl">
          <h1
            id={headingId}
            className="text-4xl font-bold tracking-tight text-ink md:text-5xl lg:text-6xl"
          >
            {title}
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-ink-muted md:text-xl">
            {description}
          </p>
          {children && <div className="mt-8 flex flex-wrap gap-4">{children}</div>}
        </div>
      </div>
    </section>
  );
}
