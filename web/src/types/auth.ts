import type { IsoDateTime, User } from '@/types/api';
import type { WorkspaceMembership, WorkspaceRole } from '@/types/workspace';

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: number | null;
  user: User;
}

export interface UserProfile {
  userId: string;
  email: string;
  fullName: string;
  company: string;
  jobTitle: string;
  photoUrl: string;
  role: string;
  emailVerified: boolean;
  organisationName: string;
  memberships: OrganisationMembership[];
  updatedAt?: IsoDateTime;
  hasBrandingLogo: boolean;
}

/** Workspace membership scoped to the signed-in user's organisation. */
export interface OrganisationMembership {
  workspaceId: string;
  workspaceName: string;
  role: WorkspaceRole;
  userId: string;
}

export interface SignInInput {
  email: string;
  password: string;
}

export interface SignUpInput {
  email: string;
  password: string;
  fullName: string;
  company?: string;
}

export interface ForgotPasswordInput {
  email: string;
}

export interface UpdateProfileInput {
  fullName?: string;
  company?: string;
  jobTitle?: string;
}

export interface BrandingLogo {
  hasLogo: boolean;
  dataUrl?: string | null;
}

export type { WorkspaceMembership };
