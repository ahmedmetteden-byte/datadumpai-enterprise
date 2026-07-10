import Link from "next/link";
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { SITE } from "@/lib/site";

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline";
type ButtonSize = "sm" | "md" | "lg";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-500 text-white hover:bg-brand-600 shadow-md hover:shadow-lg border border-transparent",
  secondary:
    "bg-white text-ink border border-surface-border hover:border-brand-300 hover:bg-brand-50",
  ghost: "text-ink-muted hover:text-brand-500 hover:bg-brand-50",
  outline:
    "border border-white/30 text-white hover:bg-white/10 backdrop-blur-sm",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-5 py-2.5 text-sm font-medium",
  lg: "px-7 py-3.5 text-base font-semibold",
};

const focusClasses =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500";

type SharedProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
  external?: boolean;
};

type ButtonAsLinkProps = SharedProps &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof SharedProps> & {
    href: string;
  };

type ButtonAsButtonProps = SharedProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    href?: undefined;
  };

type ButtonProps = ButtonAsLinkProps | ButtonAsButtonProps;

function buildClasses(variant: ButtonVariant, size: ButtonSize, className: string) {
  return `inline-flex items-center justify-center rounded-xl transition-all duration-200 ${focusClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`;
}

function ExternalHint() {
  return <span className="sr-only"> (opens in new tab)</span>;
}

export function Button(props: ButtonProps) {
  const {
    variant = "primary",
    size = "md",
    className = "",
    children,
    external,
    href,
    ...rest
  } = props;

  const classes = buildClasses(variant, size, className);

  if (href) {
    if (external) {
      const anchorProps = rest as AnchorHTMLAttributes<HTMLAnchorElement>;
      return (
        <a
          href={href}
          className={classes}
          target="_blank"
          rel="noopener noreferrer"
          {...anchorProps}
        >
          {children}
          <ExternalHint />
        </a>
      );
    }
    const anchorProps = rest as AnchorHTMLAttributes<HTMLAnchorElement>;
    return (
      <Link href={href} className={classes} {...anchorProps}>
        {children}
      </Link>
    );
  }

  const buttonProps = rest as ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button type="button" className={classes} {...buttonProps}>
      {children}
    </button>
  );
}

export function LaunchAppButton({
  size = "md",
  variant = "primary",
  className = "",
  children = "Launch App",
}: {
  size?: ButtonSize;
  variant?: ButtonVariant;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <Button
      href={SITE.appUrl}
      external
      variant={variant}
      size={size}
      className={className}
      aria-label={`${typeof children === "string" ? children : "Launch App"} — opens DataDumpAI application`}
    >
      {children}
    </Button>
  );
}
