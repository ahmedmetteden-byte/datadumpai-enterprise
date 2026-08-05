import { mockLatency, isMockApiEnabled } from '@/api/config';
import { getSupabaseClient, getSupabaseConfigErrorMessage } from '@/lib/supabase';
import { mockUser } from '@/api/mock/data';
import {
  logAuth,
  logAuthStateChanged,
  summarizeSession,
} from '@/utils/debugAuth';
import type { User } from '@/types/api';
import type {
  AuthSession,
  ForgotPasswordInput,
  SignInInput,
  SignUpInput,
} from '@/types/auth';

const MOCK_SESSION_KEY = 'datadump.auth.session';
const MOCK_PROFILE_KEY = 'datadump.auth.profile';

function syncMockProfile(user: User, company = 'My organisation') {
  try {
    const existingRaw = localStorage.getItem(MOCK_PROFILE_KEY);
    const existing = existingRaw
      ? (JSON.parse(existingRaw) as Record<string, unknown>)
      : {};
    const profile = {
      ...existing,
      userId: user.id,
      email: user.email,
      fullName: user.fullName,
      company:
        typeof existing.company === 'string' && existing.company
          ? existing.company
          : company,
      organisationName:
        typeof existing.organisationName === 'string' &&
        existing.organisationName
          ? existing.organisationName
          : company,
      emailVerified: user.emailVerified,
    };
    localStorage.setItem(MOCK_PROFILE_KEY, JSON.stringify(profile));
  } catch {
    // ignore
  }
}

export class AuthError extends Error {
  readonly code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = 'AuthError';
    this.code = code;
  }
}

export interface AuthService {
  getSession(): Promise<AuthSession | null>;
  signIn(input: SignInInput): Promise<AuthSession>;
  signUp(input: SignUpInput): Promise<AuthSession | null>;
  signOut(): Promise<void>;
  sendPasswordReset(input: ForgotPasswordInput): Promise<void>;
  onAuthStateChange(
    callback: (session: AuthSession | null) => void,
  ): () => void;
}

function mapUser(raw: {
  id: string;
  email?: string | null;
  email_confirmed_at?: string | null;
  user_metadata?: Record<string, unknown> | null;
}): User {
  const meta = raw.user_metadata ?? {};
  const fullName =
    typeof meta.full_name === 'string'
      ? meta.full_name
      : typeof meta.fullName === 'string'
        ? meta.fullName
        : '';

  return {
    id: raw.id,
    email: raw.email ?? '',
    fullName,
    emailVerified: Boolean(raw.email_confirmed_at),
  };
}

function mapSupabaseSession(session: {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
  user: {
    id: string;
    email?: string | null;
    email_confirmed_at?: string | null;
    user_metadata?: Record<string, unknown> | null;
  };
}): AuthSession {
  return {
    accessToken: session.access_token,
    refreshToken: session.refresh_token,
    expiresAt: session.expires_at ?? null,
    user: mapUser(session.user),
  };
}

function readMockSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(MOCK_SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

function writeMockSession(session: AuthSession | null) {
  try {
    if (session) {
      localStorage.setItem(MOCK_SESSION_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(MOCK_SESSION_KEY);
    }
  } catch {
    // ignore quota / private mode
  }
}

/** Phase 1 local auth — persists JWT-shaped session in localStorage. */
export class MockAuthService implements AuthService {
  private listeners = new Set<(session: AuthSession | null) => void>();

  private notify(session: AuthSession | null) {
    for (const listener of this.listeners) {
      listener(session);
    }
  }

  async getSession(): Promise<AuthSession | null> {
    logAuth('AuthService.getSession (mock)');
    await mockLatency(40);
    const session = readMockSession();
    logAuth('AuthService.getSession (mock) result', summarizeSession(session));
    return session;
  }

  async signIn(input: SignInInput): Promise<AuthSession> {
    logAuth('AuthService.signIn (mock)', { email: input.email });
    await mockLatency(220);
    const email = input.email.trim().toLowerCase();
    if (!email || !input.password) {
      throw new AuthError('Enter your email and password.');
    }
    if (input.password.length < 6) {
      throw new AuthError('Invalid email or password.', 'invalid_credentials');
    }

    const session: AuthSession = {
      accessToken: `mock_access_${btoa(email)}`,
      refreshToken: `mock_refresh_${btoa(email)}`,
      expiresAt: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7,
      user: {
        ...mockUser,
        id: mockUser.id,
        email,
        fullName:
          email === mockUser.email.toLowerCase()
            ? mockUser.fullName
            : email.split('@')[0].replace(/[._]/g, ' '),
        emailVerified: true,
      },
    };

    writeMockSession(session);
    syncMockProfile(session.user);
    this.notify(session);
    logAuth('AuthService.signIn (mock) success', summarizeSession(session));
    return session;
  }

  async signUp(input: SignUpInput): Promise<AuthSession | null> {
    await mockLatency(280);
    const email = input.email.trim().toLowerCase();
    if (!email || !input.password) {
      throw new AuthError('Enter your email and password.');
    }
    if (input.password.length < 8) {
      throw new AuthError('Password must be at least 8 characters.');
    }

    const session: AuthSession = {
      accessToken: `mock_access_${btoa(email)}`,
      refreshToken: `mock_refresh_${btoa(email)}`,
      expiresAt: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7,
      user: {
        id: `usr_${Date.now().toString(36)}`,
        email,
        fullName: input.fullName.trim(),
        emailVerified: true,
      },
    };

    writeMockSession(session);
    syncMockProfile(session.user, input.company?.trim() || 'Personal');
    this.notify(session);
    return session;
  }

  async signOut(): Promise<void> {
    logAuth('AuthService.signOut (mock)');
    await mockLatency(80);
    writeMockSession(null);
    this.notify(null);
  }

  async sendPasswordReset(input: ForgotPasswordInput): Promise<void> {
    await mockLatency(200);
    if (!input.email.trim()) {
      throw new AuthError('Enter your email address.');
    }
    // Mock always succeeds — no email is sent in Phase 1.
  }

  onAuthStateChange(
    callback: (session: AuthSession | null) => void,
  ): () => void {
    logAuth('AuthService.onAuthStateChange subscribed (mock)');
    const wrapped = (session: AuthSession | null) => {
      logAuthStateChanged(session);
      callback(session);
    };
    this.listeners.add(wrapped);
    return () => {
      this.listeners.delete(wrapped);
    };
  }
}

/** Production auth — Supabase Auth (JWT + bcrypt hashing server-side). */
export class SupabaseAuthService implements AuthService {
  private client() {
    const supabase = getSupabaseClient();
    if (!supabase) {
      throw new AuthError(getSupabaseConfigErrorMessage());
    }
    return supabase;
  }

  async getSession(): Promise<AuthSession | null> {
    logAuth('AuthService.getSession (supabase)');
    const { data, error } = await this.client().auth.getSession();
    if (error) {
      logAuth('AuthService.getSession (supabase) error', {
        message: error.message,
        name: error.name,
      });
      throw new AuthError(error.message, error.name);
    }
    if (!data.session) {
      logAuth('AuthService.getSession (supabase) result', summarizeSession(null));
      return null;
    }
    const mapped = mapSupabaseSession(data.session);
    logAuth('AuthService.getSession (supabase) result', summarizeSession(mapped));
    return mapped;
  }

  async signIn(input: SignInInput): Promise<AuthSession> {
    logAuth('AuthService.signIn (supabase)', { email: input.email });
    const email = input.email.trim().toLowerCase();
    const { data, error } = await this.client().auth.signInWithPassword({
      email,
      password: input.password,
    });

    if (error) {
      logAuth('AuthService.signIn (supabase) error', {
        message: error.message,
        name: error.name,
      });
      throw new AuthError(error.message, error.name);
    }
    if (!data.session) {
      throw new AuthError('Sign-in did not return a session.');
    }
    const mapped = mapSupabaseSession(data.session);
    logAuth('AuthService.signIn (supabase) success', summarizeSession(mapped));
    return mapped;
  }

  async signUp(input: SignUpInput): Promise<AuthSession | null> {
    const email = input.email.trim().toLowerCase();
    if (input.password.length < 8) {
      throw new AuthError('Password must be at least 8 characters.');
    }

    const { data, error } = await this.client().auth.signUp({
      email,
      password: input.password,
      options: {
        data: {
          full_name: input.fullName.trim(),
          company: input.company?.trim() ?? '',
        },
        emailRedirectTo: `${window.location.origin}/auth/login`,
      },
    });

    if (error) {
      throw new AuthError(error.message, error.name);
    }

    // Email confirmation may defer the session.
    if (!data.session) {
      return null;
    }
    return mapSupabaseSession(data.session);
  }

  async signOut(): Promise<void> {
    logAuth('AuthService.signOut (supabase)');
    const { error } = await this.client().auth.signOut();
    if (error) {
      logAuth('AuthService.signOut (supabase) error', {
        message: error.message,
      });
      throw new AuthError(error.message, error.name);
    }
    logAuth('AuthService.signOut (supabase) complete');
  }

  async sendPasswordReset(input: ForgotPasswordInput): Promise<void> {
    const email = input.email.trim().toLowerCase();
    if (!email) {
      throw new AuthError('Enter your email address.');
    }

    const { error } = await this.client().auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/login`,
    });

    if (error) {
      throw new AuthError(error.message, error.name);
    }
  }

  onAuthStateChange(
    callback: (session: AuthSession | null) => void,
  ): () => void {
    logAuth('AuthService.onAuthStateChange subscribed (supabase)');
    const { data } = this.client().auth.onAuthStateChange((_event, session) => {
      const mapped = session ? mapSupabaseSession(session) : null;
      logAuthStateChanged(mapped);
      callback(mapped);
    });
    return () => {
      data.subscription.unsubscribe();
    };
  }
}

export function createAuthService(): AuthService {
  // Production: Supabase Auth is the only provider — never fall back to mock.
  if (import.meta.env.PROD) {
    return new SupabaseAuthService();
  }
  // Local offline demos only when explicitly enabled.
  if (isMockApiEnabled()) {
    return new MockAuthService();
  }
  return new SupabaseAuthService();
}
