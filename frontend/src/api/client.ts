/**
 * Typed API client for the ReEngrave backend.
 * All functions return typed responses matching backend Pydantic schemas.
 * Includes JWT injection and auto-refresh on 401.
 */

import axios, { type AxiosRequestConfig } from 'axios';
import type {
  AutoAcceptRule,
  CheckoutResponse,
  ExportFormat,
  FlaggedDifference,
  HumanDecision,
  IMSLPSearchResult,
  KnowledgePattern,
  LearningReport,
  PaymentStatus,
  Score,
  User,
} from '../types';

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // needed for httpOnly refresh cookie
});

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

let _accessToken: string | null = null;
let _refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

// ---------------------------------------------------------------------------
// Interceptors
// ---------------------------------------------------------------------------

// Inject Authorization header
api.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers = config.headers ?? {};
    config.headers['Authorization'] = `Bearer ${_accessToken}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config as AxiosRequestConfig & { _retry?: boolean };
    const status = err.response?.status;

    // Only retry once, and not for auth endpoints (prevents infinite loop)
    if (
      status === 401 &&
      !original._retry &&
      !original.url?.includes('/api/auth/')
    ) {
      original._retry = true;

      // Deduplicate concurrent refresh calls
      if (!_refreshPromise) {
        _refreshPromise = axios
          .post(
            `${import.meta.env.VITE_API_URL ?? ''}/api/auth/refresh`,
            {},
            { withCredentials: true }
          )
          .then((r) => {
            const token: string = r.data.access_token;
            setAccessToken(token);
            return token;
          })
          .catch(() => {
            setAccessToken(null);
            return null;
          })
          .finally(() => {
            _refreshPromise = null;
          });
      }

      const newToken = await _refreshPromise;
      if (newToken) {
        original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${newToken}` };
        return api(original);
      }
    }

    return Promise.reject(err);
  }
);

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function authLogin(
  email: string,
  password: string
): Promise<{ access_token: string; user: User }> {
  const res = await api.post('/api/auth/login', { email, password });
  return res.data;
}

export async function authRegister(
  email: string,
  password: string,
  name?: string
): Promise<{ access_token: string; user: User }> {
  const res = await api.post('/api/auth/register', { email, password, name });
  return res.data;
}

export async function authRefresh(): Promise<{ access_token: string; user: User }> {
  const res = await api.post('/api/auth/refresh');
  return res.data;
}

export async function authLogout(): Promise<void> {
  await api.post('/api/auth/logout');
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>('/api/auth/me');
  return res.data;
}

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------

export async function checkVisionAccess(scoreId: string): Promise<PaymentStatus> {
  const res = await api.get<PaymentStatus>('/api/payments/status', {
    params: { score_id: scoreId },
  });
  return res.data;
}

export async function createCheckoutSession(scoreId: string): Promise<CheckoutResponse> {
  const res = await api.post<CheckoutResponse>('/api/payments/checkout', {
    score_id: scoreId,
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// IMSLP
// ---------------------------------------------------------------------------

export async function searchIMSLP(
  query: string,
  maxResults = 10
): Promise<IMSLPSearchResult[]> {
  const res = await api.get<IMSLPSearchResult[]>('/api/imslp/search', {
    params: { q: query, max_results: maxResults },
  });
  return res.data;
}

export async function downloadScore(
  url: string,
  title: string,
  composer: string,
  era: string
): Promise<{ score_id: string; status: string }> {
  const res = await api.post('/api/imslp/download', {
    url,
    score_title: title,
    composer,
    era,
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// File import
// ---------------------------------------------------------------------------

export async function uploadPDF(
  file: File,
  title: string,
  composer: string,
  era: string
): Promise<Score> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  form.append('composer', composer);
  form.append('era', era);

  const res = await api.post<Score>('/api/import/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function uploadMusicXML(
  file: File,
  title: string,
  composer: string,
  era: string
): Promise<Score> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  form.append('composer', composer);
  form.append('era', era);

  const res = await api.post<Score>('/api/import/musicxml', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// Scores CRUD
// ---------------------------------------------------------------------------

export async function listScores(): Promise<Score[]> {
  const res = await api.get<Score[]>('/api/scores');
  return res.data;
}

export async function getScore(id: string): Promise<Score> {
  const res = await api.get<Score>(`/api/scores/${id}`);
  return res.data;
}

export async function deleteScore(id: string): Promise<{ deleted: string }> {
  const res = await api.delete(`/api/scores/${id}`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Processing
// ---------------------------------------------------------------------------

export async function runOMR(
  scoreId: string
): Promise<{ score_id: string; status: string }> {
  const res = await api.post(`/api/scores/${scoreId}/process/omr`);
  return res.data;
}

export async function runComparison(
  scoreId: string
): Promise<{ score_id: string; status: string }> {
  const res = await api.post(`/api/scores/${scoreId}/process/compare`);
  return res.data;
}

export async function getScoreStatus(
  scoreId: string
): Promise<{ score_id: string; status: string; updated_at: string }> {
  const res = await api.get(`/api/scores/${scoreId}/status`);
  return res.data;
}

// ---------------------------------------------------------------------------
// Review / diffs
// ---------------------------------------------------------------------------

export async function getDiffs(scoreId: string): Promise<FlaggedDifference[]> {
  const res = await api.get<FlaggedDifference[]>(`/api/scores/${scoreId}/diffs`);
  return res.data;
}

export async function recordDecision(
  diffId: string,
  decision: HumanDecision,
  editValue?: string
): Promise<FlaggedDifference> {
  const res = await api.patch<FlaggedDifference>(`/api/diffs/${diffId}/decision`, {
    decision,
    edit_value: editValue,
  });
  return res.data;
}

export async function bulkDecide(
  scoreId: string,
  diffIds: string[],
  decision: 'accept' | 'reject'
): Promise<{ updated: number }> {
  const res = await api.post(`/api/scores/${scoreId}/diffs/bulk-decide`, {
    diff_ids: diffIds,
    decision,
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

/**
 * Trigger score export and return a Blob URL for download.
 * The browser will prompt the user to save the file.
 */
export async function exportScore(
  scoreId: string,
  format: ExportFormat
): Promise<string> {
  const res = await api.get(`/api/scores/${scoreId}/export`, {
    params: { format },
    responseType: 'blob',
  });
  return URL.createObjectURL(res.data as Blob);
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export async function getLearningReport(): Promise<LearningReport> {
  const res = await api.get<LearningReport>('/api/analytics/report');
  return res.data;
}

export async function getPatterns(): Promise<KnowledgePattern[]> {
  const res = await api.get<KnowledgePattern[]>('/api/analytics/patterns');
  return res.data;
}

export async function triggerAnalyticsUpdate(): Promise<{ status: string }> {
  const res = await api.post('/api/analytics/update');
  return res.data;
}

export async function getAutoRules(): Promise<AutoAcceptRule[]> {
  const res = await api.get<AutoAcceptRule[]>('/api/analytics/auto-rules');
  return res.data;
}

export async function triggerFinetuningExport(): Promise<{
  status: string;
  path: string;
}> {
  const res = await api.get('/api/analytics/finetuning-export');
  return res.data;
}
