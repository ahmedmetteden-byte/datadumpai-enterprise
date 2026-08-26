import { apiRequest, apiUpload } from '@/api/client';
import { mockLatency, isMockApiEnabled, type ServiceAuth } from '@/api/config';
import type { BrandingLogo } from '@/types/auth';

export interface BrandingService {
  getLogo(auth?: ServiceAuth): Promise<BrandingLogo>;
  uploadLogo(file: File, auth?: ServiceAuth): Promise<BrandingLogo>;
  removeLogo(auth?: ServiceAuth): Promise<BrandingLogo>;
}

const MOCK_LOGO_KEY = 'datadump.branding.logo';

function readMockLogo(): BrandingLogo {
  try {
    const raw = localStorage.getItem(MOCK_LOGO_KEY);
    if (raw) {
      return JSON.parse(raw) as BrandingLogo;
    }
  } catch {
    // fall through
  }
  return { hasLogo: false };
}

function writeMockLogo(logo: BrandingLogo) {
  try {
    localStorage.setItem(MOCK_LOGO_KEY, JSON.stringify(logo));
  } catch {
    // ignore
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read file.'));
    reader.readAsDataURL(file);
  });
}

export class MockBrandingService implements BrandingService {
  async getLogo(): Promise<BrandingLogo> {
    await mockLatency(80);
    return readMockLogo();
  }

  async uploadLogo(file: File): Promise<BrandingLogo> {
    await mockLatency(200);
    const dataUrl = await readFileAsDataUrl(file);
    const logo: BrandingLogo = { hasLogo: true, dataUrl };
    writeMockLogo(logo);
    return logo;
  }

  async removeLogo(): Promise<BrandingLogo> {
    await mockLatency(120);
    const logo: BrandingLogo = { hasLogo: false };
    writeMockLogo(logo);
    return logo;
  }
}

export class HttpBrandingService implements BrandingService {
  async getLogo(auth?: ServiceAuth): Promise<BrandingLogo> {
    return apiRequest<BrandingLogo>('/api/v1/me/branding/logo', {
      token: auth?.accessToken,
    });
  }

  async uploadLogo(file: File, auth?: ServiceAuth): Promise<BrandingLogo> {
    const form = new FormData();
    form.append('file', file, file.name);
    return apiUpload<BrandingLogo>('/api/v1/me/branding/logo', form, {
      token: auth?.accessToken,
    });
  }

  async removeLogo(auth?: ServiceAuth): Promise<BrandingLogo> {
    return apiRequest<BrandingLogo>('/api/v1/me/branding/logo', {
      method: 'DELETE',
      token: auth?.accessToken,
    });
  }
}

export function createBrandingService(): BrandingService {
  if (!import.meta.env.PROD && isMockApiEnabled()) {
    return new MockBrandingService();
  }
  return new HttpBrandingService();
}
