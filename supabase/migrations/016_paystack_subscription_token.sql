-- Paystack subscription_code + email_token — required by Paystack's
-- POST /subscription/disable endpoint to actually stop recurring billing.
-- Without these, cancelling in the product only updated payment_subscription_id
-- (which stores the *plan* code, not a per-customer subscription identifier)
-- and never told Paystack to stop billing the customer's saved authorization.

alter table public.user_usage
    add column if not exists paystack_subscription_code text,
    add column if not exists paystack_subscription_token text;
