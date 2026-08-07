import { NextResponse } from "next/server";

// Server-only — never prefixed with NEXT_PUBLIC_, so it never ships to the browser.
// Both processes run on the same host, so this stays a same-host server-to-server
// call and never needs browser CORS.
const DATADUMP_API_URL = (process.env.DATADUMP_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/+$/,
  ""
);

interface ContactPayload {
  firstName?: unknown;
  lastName?: unknown;
  email?: unknown;
  company?: unknown;
  subject?: unknown;
  message?: unknown;
  honeypot?: unknown;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function POST(request: Request) {
  let payload: ContactPayload;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const firstName = asString(payload.firstName);
  const lastName = asString(payload.lastName);
  const email = asString(payload.email);
  const message = asString(payload.message);

  if (!firstName || !lastName || !email || !message) {
    return NextResponse.json(
      { error: "First name, last name, email, and message are required." },
      { status: 400 }
    );
  }

  const body = {
    firstName,
    lastName,
    email,
    company: asString(payload.company) || undefined,
    subject: asString(payload.subject) || "general",
    message,
    honeypot: asString(payload.honeypot) || undefined,
  };

  try {
    const response = await fetch(`${DATADUMP_API_URL}/api/v1/public/contact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Could not send your message. Please try again later." },
        { status: response.status === 429 ? 429 : 502 }
      );
    }

    const data = (await response.json()) as { status: "sent" | "skipped" };
    return NextResponse.json({ status: data.status });
  } catch {
    return NextResponse.json(
      { error: "Could not reach the server. Please try again later." },
      { status: 502 }
    );
  }
}
