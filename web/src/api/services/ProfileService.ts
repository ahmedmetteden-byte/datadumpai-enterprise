import { apiRequest } from '@/api/client';
import { mockLatency, isMockApiEnabled, type ServiceAuth } from '@/api/config';
import { mockUser, mockWorkspaces } from '@/api/mock/data';
import { getSupabaseClient } from '@/lib/supabase';
import { logAuth } from '@/utils/debugAuth';
import type {
  OrganisationMembership,
  UpdateProfileInput,
  UserProfile,
} from '@/types/auth';
import type { WorkspaceRole } from '@/types/workspace';

export interface ProfileService {
  getProfile(auth?: ServiceAuth): Promise<UserProfile>;
  updateProfile(
    input: UpdateProfileInput,
    auth?: ServiceAuth,
  ): Promise<UserProfile>;
  listOrganisationMemberships(
    auth?: ServiceAuth,
  ): Promise<OrganisationMembership[]>;
}

const MOCK_PROFILE_KEY = 'datadump.auth.profile';

function defaultMockProfile(email?: string, fullName?: string): UserProfile {
  return {
    userId: mockUser.id,
    email: email ?? mockUser.email,
    fullName: fullName ?? mockUser.fullName,
    company: '',
    jobTitle: '',
    photoUrl: '',
    role: 'user',
    emailVerified: true,
    organisationName: '',
    memberships: mockWorkspaces.map((ws, index) => ({
      workspaceId: ws.id,
      workspaceName: ws.name,
      role: (index === 0 ? 'owner' : 'admin') as WorkspaceRole,
      userId: mockUser.id,
    })),
  };
}

function readMockProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(MOCK_PROFILE_KEY);
    if (raw) {
      return JSON.parse(raw) as UserProfile;
    }
  } catch {
    // fall through
  }
  return defaultMockProfile();
}

function writeMockProfile(profile: UserProfile) {
  try {
    localStorage.setItem(MOCK_PROFILE_KEY, JSON.stringify(profile));
  } catch {
    // ignore
  }
}

export class MockProfileService implements ProfileService {
  async getProfile(_auth?: ServiceAuth): Promise<UserProfile> {
    await mockLatency(120);
    return readMockProfile();
  }

  async updateProfile(
    input: UpdateProfileInput,
    _auth?: ServiceAuth,
  ): Promise<UserProfile> {
    await mockLatency(160);
    const current = readMockProfile();
    const next: UserProfile = {
      ...current,
      fullName: input.fullName?.trim() ?? current.fullName,
      company: input.company?.trim() ?? current.company,
      jobTitle: input.jobTitle?.trim() ?? current.jobTitle,
      organisationName: input.company?.trim() ?? current.organisationName,
      updatedAt: new Date().toISOString(),
    };
    writeMockProfile(next);
    return next;
  }

  async listOrganisationMemberships(
    _auth?: ServiceAuth,
  ): Promise<OrganisationMembership[]> {
    await mockLatency(80);
    return readMockProfile().memberships;
  }
}

export class HttpProfileService implements ProfileService {
  async getProfile(auth?: ServiceAuth): Promise<UserProfile> {
    const url = '/api/v1/me/profile';
    const token = auth?.accessToken ?? null;
    logAuth('ProfileService.getProfile BEFORE', {
      url,
      tokenExists: Boolean(token),
      tokenPrefix: token ? token.slice(0, 20) : null,
    });
    try {
      const profile = await apiRequest<UserProfile>(url, {
        token,
      });
      logAuth('ProfileService.getProfile AFTER', {
        url,
        status: 200,
        responseBody: profile,
      });
      return profile;
    } catch (err) {
      logAuth('ProfileService.getProfile AFTER (error)', {
        url,
        status: err instanceof Error && 'status' in err ? (err as { status: number }).status : 'unknown',
        responseBody: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }
  }

  async updateProfile(
    input: UpdateProfileInput,
    auth?: ServiceAuth,
  ): Promise<UserProfile> {
    return apiRequest<UserProfile>('/api/v1/me/profile', {
      method: 'PATCH',
      body: input,
      token: auth?.accessToken,
    });
  }

  async listOrganisationMemberships(
    auth?: ServiceAuth,
  ): Promise<OrganisationMembership[]> {
    return apiRequest<OrganisationMembership[]>('/api/v1/me/memberships', {
      token: auth?.accessToken,
    });
  }
}

/** Reads `user_profiles` + owned projects via Supabase RLS (JWT). */
export class SupabaseProfileService implements ProfileService {
  private client() {
    const supabase = getSupabaseClient();
    if (!supabase) {
      throw new Error('Supabase is not configured.');
    }
    return supabase;
  }

  async getProfile(auth?: ServiceAuth): Promise<UserProfile> {
    const supabase = this.client();
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser(auth?.accessToken ?? undefined);

    if (userError || !user) {
      throw new Error(userError?.message ?? 'Not authenticated');
    }

    const { data: profile, error } = await supabase
      .from('user_profiles')
      .select(
        'user_id, full_name, company, job_title, photo_url, role, email, updated_at',
      )
      .eq('user_id', user.id)
      .maybeSingle();

    if (error) {
      throw new Error(error.message);
    }

    const memberships = await this.listOrganisationMemberships(auth);
    const company = profile?.company ?? '';

    return {
      userId: user.id,
      email: profile?.email || user.email || '',
      fullName:
        profile?.full_name ||
        (typeof user.user_metadata?.full_name === 'string'
          ? user.user_metadata.full_name
          : ''),
      company,
      jobTitle: profile?.job_title ?? '',
      photoUrl: profile?.photo_url ?? '',
      role: profile?.role ?? 'user',
      emailVerified: Boolean(user.email_confirmed_at),
      organisationName: company || 'Personal',
      memberships,
      updatedAt: profile?.updated_at,
    };
  }

  async updateProfile(
    input: UpdateProfileInput,
    auth?: ServiceAuth,
  ): Promise<UserProfile> {
    const supabase = this.client();
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser(auth?.accessToken ?? undefined);

    if (userError || !user) {
      throw new Error(userError?.message ?? 'Not authenticated');
    }

    const patch: Record<string, string> = {};
    if (input.fullName !== undefined) patch.full_name = input.fullName.trim();
    if (input.company !== undefined) patch.company = input.company.trim();
    if (input.jobTitle !== undefined) patch.job_title = input.jobTitle.trim();

    const { error } = await supabase
      .from('user_profiles')
      .update(patch)
      .eq('user_id', user.id);

    if (error) {
      throw new Error(error.message);
    }

    return this.getProfile(auth);
  }

  async listOrganisationMemberships(
    auth?: ServiceAuth,
  ): Promise<OrganisationMembership[]> {
    const supabase = this.client();
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser(auth?.accessToken ?? undefined);

    if (userError || !user) {
      throw new Error(userError?.message ?? 'Not authenticated');
    }

    // Today ownership is per-user via projects.user_id (no workspace_members table yet).
    const { data, error } = await supabase
      .from('projects')
      .select('id, name, user_id')
      .eq('user_id', user.id)
      .order('name');

    if (error) {
      throw new Error(error.message);
    }

    return (data ?? []).map((row) => ({
      workspaceId: row.id as string,
      workspaceName: row.name as string,
      role: 'owner' as WorkspaceRole,
      userId: row.user_id as string,
    }));
  }
}

export function createProfileService(): ProfileService {
  // Offline demos only — production always uses the product API (JWT).
  if (!import.meta.env.PROD && isMockApiEnabled()) {
    return new MockProfileService();
  }
  return new HttpProfileService();
}
