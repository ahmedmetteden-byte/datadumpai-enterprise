import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { ServiceAuth } from '@/api/config';
import {
  createAuthService,
  type AuthService,
} from '@/api/services/AuthService';
import {
  createProfileService,
  type ProfileService,
} from '@/api/services/ProfileService';
import { setUnauthorizedHandler } from '@/lib/authEvents';
import {
  logAuth,
  logUnauthorizedDiagnostic,
  summarizeSession,
} from '@/utils/debugAuth';
import type {
  AuthSession,
  ForgotPasswordInput,
  SignInInput,
  SignUpInput,
  UserProfile,
} from '@/types/auth';
import type { User } from '@/types/api';

interface AuthContextValue {
  user: User | null;
  session: AuthSession | null;
  profile: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  accessToken: string | null;
  auth: ServiceAuth;
  signIn: (input: SignInInput) => Promise<void>;
  signUp: (input: SignUpInput) => Promise<'session' | 'verify_email'>;
  signOut: () => Promise<void>;
  sendPasswordReset: (input: ForgotPasswordInput) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const authService: AuthService = createAuthService();
const profileService: ProfileService = createProfileService();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSessionLocally = useCallback(() => {
    setSession(null);
    setProfile(null);
  }, []);

  const loadProfile = useCallback(async (active: AuthSession | null) => {
    if (!active) {
      setProfile(null);
      return;
    }
    try {
      const next = await profileService.getProfile({
        accessToken: active.accessToken,
      });
      setProfile(next);
    } catch {
      setProfile({
        userId: active.user.id,
        email: active.user.email,
        fullName: active.user.fullName,
        company: '',
        jobTitle: '',
        photoUrl: '',
        role: 'user',
        emailVerified: active.user.emailVerified,
        organisationName: 'Personal',
        memberships: [],
        hasBrandingLogo: false,
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      logAuth('AUTH BOOTSTRAP', {
        note: 'Calling authService.getSession()…',
      });
      try {
        const existing = await authService.getSession();
        if (cancelled) return;
        logAuth('AUTH BOOTSTRAP — getSession result', summarizeSession(existing));
        setSession(existing);
        await loadProfile(existing);
      } catch (err) {
        logAuth('AUTH BOOTSTRAP — getSession FAILED', {
          error: err instanceof Error ? err.message : String(err),
        });
        if (!cancelled) {
          setSession(null);
          setProfile(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void bootstrap();

    const unsubscribe = authService.onAuthStateChange((next) => {
      logAuth('AUTH PROVIDER — onAuthStateChange', summarizeSession(next));
      setSession(next);
      void loadProfile(next);
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [loadProfile]);

  // DIAGNOSTICS: log 401s only — do not sign out, clear session, or redirect.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      logUnauthorizedDiagnostic();
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const signIn = useCallback(async (input: SignInInput) => {
    logAuth('AUTH PROVIDER — signIn', { email: input.email });
    const next = await authService.signIn(input);
    logAuth('AUTH PROVIDER — signIn success', summarizeSession(next));
    setSession(next);
    await loadProfile(next);
  }, [loadProfile]);

  const signUp = useCallback(
    async (input: SignUpInput) => {
      logAuth('AUTH PROVIDER — signUp', { email: input.email });
      const next = await authService.signUp(input);
      if (!next) {
        logAuth('AUTH PROVIDER — signUp verify_email');
        return 'verify_email' as const;
      }
      logAuth('AUTH PROVIDER — signUp session', summarizeSession(next));
      setSession(next);
      await loadProfile(next);
      return 'session' as const;
    },
    [loadProfile],
  );

  const signOut = useCallback(async () => {
    logAuth('AUTH PROVIDER — signOut (user-initiated)');
    await authService.signOut();
    clearSessionLocally();
  }, [clearSessionLocally]);

  const sendPasswordReset = useCallback(async (input: ForgotPasswordInput) => {
    await authService.sendPasswordReset(input);
  }, []);

  const refreshProfile = useCallback(async () => {
    await loadProfile(session);
  }, [loadProfile, session]);

  const auth = useMemo<ServiceAuth>(
    () => ({ accessToken: session?.accessToken ?? null }),
    [session?.accessToken],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      session,
      profile,
      loading,
      isAuthenticated: Boolean(session?.accessToken),
      accessToken: session?.accessToken ?? null,
      auth,
      signIn,
      signUp,
      signOut,
      sendPasswordReset,
      refreshProfile,
    }),
    [
      session,
      profile,
      loading,
      auth,
      signIn,
      signUp,
      signOut,
      sendPasswordReset,
      refreshProfile,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
