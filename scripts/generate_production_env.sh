#!/usr/bin/env bash
# Generate production .env for DataDumpAI Enterprise v1.0 from the legacy stack.
# Run on the server only. Does not print secret values.
set -euo pipefail

TARGET_DIR="${1:-/opt/datadumpai-enterprise-v1}"
LEGACY_ENV="/opt/datadump-ai/backend/.env"
TARGET_ENV="$TARGET_DIR/.env"
STAGING_MODE="${STAGING_MODE:-false}"

mkdir -p "$TARGET_DIR"

read_legacy() {
  local key="$1"
  if [ -f "$LEGACY_ENV" ]; then
    grep -m1 "^${key}=" "$LEGACY_ENV" 2>/dev/null | cut -d= -f2- || true
  fi
}

OPENAI_API_KEY="$(read_legacy OPENAI_API_KEY)"
SMTP_HOST="$(read_legacy SMTP_HOST)"
SMTP_PORT="$(read_legacy SMTP_PORT)"
SMTP_USER="$(read_legacy SMTP_USERNAME)"
SMTP_PASSWORD="$(read_legacy SMTP_PASSWORD)"
SMTP_FROM="$(read_legacy SMTP_FROM_EMAIL)"
STRIPE_SECRET="$(read_legacy STRIPE_SECRET_KEY)"
STRIPE_WEBHOOK="$(read_legacy STRIPE_WEBHOOK_SECRET)"

if [ -f "$TARGET_ENV" ]; then
  SUPABASE_URL="$(grep -m1 '^SUPABASE_URL=' "$TARGET_ENV" | cut -d= -f2- || true)"
  SUPABASE_ANON_KEY="$(grep -m1 '^SUPABASE_ANON_KEY=' "$TARGET_ENV" | cut -d= -f2- || true)"
  SUPABASE_SERVICE_ROLE_KEY="$(grep -m1 '^SUPABASE_SERVICE_ROLE_KEY=' "$TARGET_ENV" | cut -d= -f2- || true)"
else
  SUPABASE_URL=""
  SUPABASE_ANON_KEY=""
  SUPABASE_SERVICE_ROLE_KEY=""
fi

AUTH_DEV_BYPASS=false
ENVIRONMENT=production
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ]; then
  if [ "$STAGING_MODE" = "true" ]; then
    ENVIRONMENT=development
    AUTH_DEV_BYPASS=true
    echo "WARNING: Supabase not configured. Staging dev auth enabled (ENVIRONMENT=development, AUTH_DEV_BYPASS=true)."
  else
    echo "ERROR: SUPABASE_URL and SUPABASE_ANON_KEY are required for production."
    exit 2
  fi
fi

cat > "$TARGET_ENV" <<EOF
# DataDumpAI Enterprise v1.0 — production
OPENAI_API_KEY=${OPENAI_API_KEY}

ENVIRONMENT=${ENVIRONMENT}
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
AUTH_REDIRECT_URL=https://getdatadump.com
AUTH_DEV_BYPASS=${AUTH_DEV_BYPASS}

DATABASE_BACKEND=supabase
STORAGE_BACKEND=supabase
SUPABASE_STORAGE_BUCKET=datadumpai-files

PAYMENTS_ENABLED=true
STRIPE_SECRET_KEY=${STRIPE_SECRET}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK}
STRIPE_STARTER_PRICE_ID=
STRIPE_PROFESSIONAL_PRICE_ID=
STRIPE_STARTER_AMOUNT_CENTS=1500
STRIPE_PROFESSIONAL_AMOUNT_CENTS=3900

PAYSTACK_SECRET_KEY=
PAYSTACK_STARTER_PLAN_CODE=
PAYSTACK_PROFESSIONAL_PLAN_CODE=
PAYSTACK_STARTER_AMOUNT_KOBO=1500000
PAYSTACK_PROFESSIONAL_AMOUNT_KOBO=3900000

BILLING_SUCCESS_URL=https://getdatadump.com
BILLING_CANCEL_URL=https://getdatadump.com
BILLING_WEBHOOK_BASE_URL=https://getdatadump.com

EMAIL_ENABLED=true
EMAIL_FROM=${SMTP_FROM:-noreply@datadumpai.com}
EMAIL_FROM_NAME=DataDumpAI
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT:-587}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_USE_TLS=true
RESEND_API_KEY=

ADMIN_USER_IDS=
ADMIN_EMAILS=

ANALYTICS_ENABLED=false
ANALYTICS_PROVIDER=local
DEBUG=false
EOF

chmod 600 "$TARGET_ENV"
mkdir -p "$TARGET_DIR/static"
if [ -f "$TARGET_DIR/assets/logo.png" ]; then
  cp "$TARGET_DIR/assets/logo.png" "$TARGET_DIR/assets/favicon.png" "$TARGET_DIR/assets/og-image.png" "$TARGET_DIR/static/"
fi
if [ -f "$TARGET_DIR/scripts/generate_seo_static.py" ]; then
  (cd "$TARGET_DIR" && python scripts/generate_seo_static.py) || true
fi
echo "Wrote $TARGET_ENV"
echo "Environment ready."
