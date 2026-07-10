# DataDumpAI Marketing Site

Production-ready public website for [DataDumpAI](https://www.getdatadump.com). This is a standalone Next.js 15 application — it does not replace the Streamlit application.

## Architecture

```
www.getdatadump.com  →  Marketing Site (this project)
                              │
                         Launch App
                              │
                              ▼
                    app.getdatadump.com  →  Streamlit App
```

The Launch App URL is configurable via environment variable, so you can point it at your current Streamlit deployment during migration.

## Quick Start

```bash
cd marketing-site
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_SITE_URL` | Canonical public site URL | `https://www.getdatadump.com` |
| `NEXT_PUBLIC_APP_URL` | Streamlit application URL (Launch App button) | `https://www.getdatadump.com` |
| `NEXT_PUBLIC_CONTACT_EMAIL` | Contact form email placeholder | `hello@getdatadump.com` |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | Google Analytics 4 Measurement ID (`G-…`) | *(empty — analytics disabled)* |
| `NEXT_PUBLIC_SENTRY_DSN` | Sentry DSN for error monitoring | *(empty — monitoring disabled)* |

### Migration Path

Initially, point `NEXT_PUBLIC_APP_URL` at your current Streamlit app:

```env
NEXT_PUBLIC_APP_URL=https://www.getdatadump.com
```

When ready to move Streamlit to a subdomain, update only the env var:

```env
NEXT_PUBLIC_APP_URL=https://app.getdatadump.com
```

No code changes required.

## Google Analytics (production)

Analytics loads **only in production** when `NEXT_PUBLIC_GA_MEASUREMENT_ID` is set.

1. Create a GA4 property at [Google Analytics](https://analytics.google.com/).
2. Add a **Web** data stream for `www.getdatadump.com`.
3. Copy the **Measurement ID** (format `G-XXXXXXXXXX`).
4. Add to your deployment environment:

```env
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

Page views are tracked automatically across App Router client navigations via `@next/third-parties/google`.

## Error Monitoring (Sentry-ready)

Monitoring is **disabled by default**. The project includes a provider abstraction so you can enable Sentry later without restructuring code.

1. Create a project at [Sentry](https://sentry.io/) and copy the **DSN**.
2. Add to your deployment environment:

```env
NEXT_PUBLIC_SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

3. When ready to activate, install the SDK and complete the adapter:

```bash
npm install @sentry/nextjs
```

Then implement `src/lib/monitoring/sentry-adapter.ts` using `Sentry.init()` and wire `captureException` / `captureMessage` to the SDK.

Route errors are reported via `app/error.tsx` and `app/global-error.tsx`. Server bootstrap runs through `src/instrumentation.ts`.

## Images

Production images live in `public/`. UI components use WebP (`logo.webp`, `datadump-hero-logo.webp`) for smaller payloads; PNG fallbacks remain for external references.

Re-optimize after replacing source assets:

```bash
npm run optimize-images
```

Requires Python 3 with Pillow (`pip install pillow`).

## Pages

- **Home** — Hero, features preview, industries, CTA
- **Features** — Full capability list
- **Solutions** — Use cases by role
- **Industries** — Sector cards
- **Pricing** — Plans with feature comparison
- **Documentation** — Sidebar navigation with placeholder docs
- **About** — Mission and values
- **Contact** — Professional contact form
- **Privacy Policy** / **Terms of Service** / **Security**

## SEO

- Server-side metadata via Next.js Metadata API (title, description, canonical, Open Graph, Twitter Cards)
- JSON-LD structured data (`SoftwareApplication` schema)
- Auto-generated `sitemap.xml` and `robots.txt`
- Favicon and Apple touch icon support

## Deployment

Build and deploy independently:

```bash
npm run build
npm start
```

Recommended hosts: Vercel, Netlify, or any Node.js hosting. Configure environment variables in your deployment platform.

### Production checklist

- [ ] Set `NEXT_PUBLIC_SITE_URL` and `NEXT_PUBLIC_APP_URL`
- [ ] Set `NEXT_PUBLIC_GA_MEASUREMENT_ID` (optional)
- [ ] Set `NEXT_PUBLIC_SENTRY_DSN` when Sentry is configured (optional)
- [ ] Run `npm run build` and verify Lighthouse scores

## Tech Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- Server Components for performance
- `@next/third-parties` for Google Analytics 4
