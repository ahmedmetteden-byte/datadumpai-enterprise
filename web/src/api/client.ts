import type { ApiErrorBody } from '@/types/api';
import { notifyUnauthorized } from '@/lib/authEvents';
import {
  logApiRequest,
  logApiResponse,
  logFirst401,
} from '@/utils/debugAuth';

const NETWORK_ERROR_MESSAGE =
  'Network error. Check your connection and try again.';

export class ApiError extends Error {
  readonly status: number;
  readonly body?: ApiErrorBody;

  constructor(message: string, status: number, body?: ApiErrorBody) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function resolveBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured && configured.length > 0) {
    return configured.replace(/\/$/, '');
  }
  return '';
}

function handleUnauthorized(status: number) {
  if (status === 401) {
    notifyUnauthorized();
  }
}

function headersToObject(headers: Headers): Record<string, string> {
  const out: Record<string, string> = {};
  headers.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

async function readBodyClone(response: Response): Promise<unknown> {
  try {
    const clone = response.clone();
    const contentType = clone.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      return await clone.json();
    }
    return await clone.text();
  } catch {
    return '[unreadable body]';
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  token?: string | null;
}

/**
 * Thin fetch wrapper for the FastAPI product API.
 * Attaches Bearer tokens the same way Streamlit does for Supabase RLS.
 * 401s notify AuthProvider for diagnostics only — no redirects here.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, token, headers, ...rest } = options;
  const url = `${resolveBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
  const method = (rest.method ?? (body !== undefined ? 'POST' : 'GET')).toUpperCase();
  const tokenPrefix = token ? token.slice(0, 20) : null;

  logApiRequest({
    url,
    method,
    hasAuthorization: Boolean(token),
    tokenPrefix,
    body,
  });

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    throw new ApiError(NETWORK_ERROR_MESSAGE, 0);
  }

  const responseBody = await readBodyClone(response);
  const responseHeaders = headersToObject(response.headers);

  logApiResponse({
    url,
    status: response.status,
    headers: responseHeaders,
    body: responseBody,
  });

  if (response.status === 401) {
    logFirst401({
      url,
      method,
      status: response.status,
      headers: responseHeaders,
      body: responseBody,
      tokenPrefix,
    });
  }

  if (!response.ok) {
    let errorBody: ApiErrorBody | undefined;
    try {
      errorBody =
        responseBody && typeof responseBody === 'object'
          ? (responseBody as ApiErrorBody)
          : undefined;
    } catch {
      errorBody = undefined;
    }

    handleUnauthorized(response.status);

    throw new ApiError(
      typeof errorBody?.detail === 'string'
        ? errorBody.detail
        : `Request failed (${response.status})`,
      response.status,
      errorBody,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    throw new ApiError(
      'API returned a non-JSON response. Is the product API running?',
      response.status,
    );
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      'API returned invalid JSON. Is the product API running?',
      response.status,
    );
  }
}

export interface UploadOptions {
  token?: string | null;
  signal?: AbortSignal;
  /** 0–100 while bytes are transferring to the API */
  onProgress?: (percent: number) => void;
}

/** Multipart upload helper with optional transfer progress (XHR). */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options: UploadOptions = {},
): Promise<T> {
  const url = `${resolveBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
  const tokenPrefix = options.token ? options.token.slice(0, 20) : null;

  logApiRequest({
    url,
    method: 'POST',
    hasAuthorization: Boolean(options.token),
    tokenPrefix,
    body: '[FormData]',
  });

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.responseType = 'json';
    xhr.setRequestHeader('Accept', 'application/json');
    if (options.token) {
      xhr.setRequestHeader('Authorization', `Bearer ${options.token}`);
    }

    if (options.signal) {
      if (options.signal.aborted) {
        reject(new DOMException('Upload aborted', 'AbortError'));
        return;
      }
      options.signal.addEventListener('abort', () => xhr.abort(), {
        once: true,
      });
    }

    xhr.upload.onprogress = (event) => {
      if (!options.onProgress || !event.lengthComputable || event.total <= 0) {
        return;
      }
      const percent = Math.max(
        0,
        Math.min(100, Math.round((event.loaded / event.total) * 100)),
      );
      options.onProgress(percent);
    };

    xhr.onload = () => {
      logApiResponse({
        url,
        status: xhr.status,
        body: xhr.response,
      });

      if (xhr.status === 401) {
        logFirst401({
          url,
          method: 'POST',
          status: xhr.status,
          body: xhr.response,
          tokenPrefix,
        });
        handleUnauthorized(401);
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        options.onProgress?.(100);
        resolve(xhr.response as T);
        return;
      }

      const errorBody = (xhr.response ?? undefined) as ApiErrorBody | undefined;
      const detail =
        typeof errorBody?.detail === 'string'
          ? errorBody.detail
          : `Upload failed (${xhr.status})`;
      reject(new ApiError(detail, xhr.status, errorBody));
    };

    xhr.onerror = () => {
      reject(new ApiError(NETWORK_ERROR_MESSAGE, 0));
    };

    xhr.onabort = () => {
      reject(new DOMException('Upload aborted', 'AbortError'));
    };

    xhr.send(formData);
  });
}
