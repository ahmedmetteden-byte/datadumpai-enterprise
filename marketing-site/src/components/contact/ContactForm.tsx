"use client";

import { useState } from "react";
import { SITE } from "@/lib/site";
import { Button } from "@/components/ui/Button";

const inputClassName =
  "mt-2 block w-full rounded-xl border border-surface-border px-4 py-2.5 text-sm transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20";

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="rounded-2xl border border-green-200 bg-green-50 p-8 text-center"
      >
        <p className="text-lg font-semibold text-green-900">Message sent</p>
        <p className="mt-2 text-sm text-green-800">
          Thank you for reaching out. Our team will respond within one business day.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor="firstName" className="block text-sm font-medium text-ink">
            First name
          </label>
          <input
            id="firstName"
            name="firstName"
            type="text"
            autoComplete="given-name"
            required
            className={inputClassName}
          />
        </div>
        <div>
          <label htmlFor="lastName" className="block text-sm font-medium text-ink">
            Last name
          </label>
          <input
            id="lastName"
            name="lastName"
            type="text"
            autoComplete="family-name"
            required
            className={inputClassName}
          />
        </div>
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium text-ink">
          Work email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          className={inputClassName}
        />
      </div>

      <div>
        <label htmlFor="company" className="block text-sm font-medium text-ink">
          Company
        </label>
        <input
          id="company"
          name="company"
          type="text"
          autoComplete="organization"
          className={inputClassName}
        />
      </div>

      <div>
        <label htmlFor="subject" className="block text-sm font-medium text-ink">
          Subject
        </label>
        <select id="subject" name="subject" className={inputClassName} defaultValue="general">
          <option value="general">General inquiry</option>
          <option value="sales">Sales &amp; Enterprise</option>
          <option value="support">Technical support</option>
          <option value="partnership">Partnership</option>
          <option value="press">Press &amp; media</option>
        </select>
      </div>

      <div>
        <label htmlFor="message" className="block text-sm font-medium text-ink">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={5}
          required
          className={inputClassName}
        />
      </div>

      <Button type="submit" size="lg" className="w-full sm:w-auto">
        Send message
      </Button>
    </form>
  );
}

export function ContactInfo() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">
          Email
        </h2>
        <a
          href={`mailto:${SITE.contactEmail}`}
          className="mt-2 block text-lg font-medium text-brand-600 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
        >
          {SITE.contactEmail}
        </a>
      </div>
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">
          Enterprise sales
        </h2>
        <p className="mt-2 text-ink-muted">
          For SSO, custom deployment, API access, and volume licensing — our
          enterprise team is ready to help.
        </p>
      </div>
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">
          Response time
        </h2>
        <p className="mt-2 text-ink-muted">
          We respond to all inquiries within one business day.
        </p>
      </div>
    </div>
  );
}
