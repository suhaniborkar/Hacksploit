// Dashboard Service Layer
// All methods fetch from the FastAPI backend at /api/v1/...
// The Vite dev proxy forwards /api → http://localhost:8000.
// Token is injected via createDashboardService(getToken) to keep the service
// stateless and testable without a React context dependency.

import type {
  Application,
  DashboardUser,
  AnalyticsSeries,
  SharedIdentifierCluster,
  FraudCluster,
  MetricCardData,
  UserRole,
} from '../types/dashboard';

type TokenGetter = () => string | null;

const BASE = '/api/v1';

// Back-end DashboardUser shape uses 'last_login_at' / 'created_at'.
// Map to the frontend camelCase contract.
interface RawUser {
  id: string;
  name: string | null;
  email: string;
  role: string;
  status?: string;
  last_login_at?: string | null;
  created_at?: string | null;
}

function mapUser(u: RawUser): DashboardUser {
  return {
    id: u.id,
    name: u.name ?? u.email,
    email: u.email,
    role: u.role as UserRole,
    status: (u.status ?? 'active') as DashboardUser['status'],
    lastLogin: u.last_login_at ?? 'Never',
    createdAt: u.created_at ?? new Date().toISOString(),
  };
}

async function apiFetch<T>(
  path: string,
  getToken: TokenGetter,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    throw new Error('Session expired. Please sign in again.');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

class DashboardService {
  private readonly getToken: TokenGetter;

  constructor(getToken: TokenGetter) {
    this.getToken = getToken;
  }

  async getSummaryMetrics(): Promise<MetricCardData[]> {
    return apiFetch<MetricCardData[]>('/dashboard/metrics', this.getToken);
  }

  async getApplications(params?: {
    status?: string;
    search?: string;
    doc_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<Application[]> {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.search) qs.set('search', params.search);
    if (params?.doc_type) qs.set('doc_type', params.doc_type);
    if (params?.skip !== undefined) qs.set('skip', String(params.skip));
    if (params?.limit !== undefined) qs.set('limit', String(params.limit));
    const query = qs.toString() ? `?${qs.toString()}` : '';
    return apiFetch<Application[]>(`/dashboard/applications${query}`, this.getToken);
  }

  async getApplicationById(id: string): Promise<Application | null> {
    try {
      return await apiFetch<Application>(`/dashboard/applications/${id}`, this.getToken);
    } catch (e) {
      if (e instanceof Error && e.message.startsWith('HTTP 404')) return null;
      throw e;
    }
  }

  async updateApplicationStatus(
    id: string,
    status: Application['status'],
    note?: string,
  ): Promise<Application | null> {
    return apiFetch<Application>(`/dashboard/applications/${id}/decision`, this.getToken, {
      method: 'POST',
      body: JSON.stringify({ status, note }),
    });
  }

  async getUsers(): Promise<DashboardUser[]> {
    const raw = await apiFetch<RawUser[]>('/auth/users', this.getToken);
    return raw.map(mapUser);
  }

  async addUser(user: {
    name: string;
    email: string;
    role: UserRole;
    password?: string;
    status?: DashboardUser['status'];
  }): Promise<DashboardUser> {
    const raw = await apiFetch<RawUser>('/auth/users', this.getToken, {
      method: 'POST',
      body: JSON.stringify({
        name: user.name,
        email: user.email,
        role: user.role,
        password: user.password ?? 'ArgusTemp2026!',
      }),
    });
    return mapUser(raw);
  }

  async deleteUser(id: string): Promise<boolean> {
    try {
      await apiFetch<unknown>(`/auth/users/${id}`, this.getToken, { method: 'DELETE' });
      return true;
    } catch {
      return false;
    }
  }

  async getAnalytics(): Promise<AnalyticsSeries> {
    return apiFetch<AnalyticsSeries>('/dashboard/analytics', this.getToken);
  }

  async getFraudClusters(): Promise<{ shared: SharedIdentifierCluster[]; rings: FraudCluster[] }> {
    return apiFetch<{ shared: SharedIdentifierCluster[]; rings: FraudCluster[] }>(
      '/dashboard/clusters',
      this.getToken,
    );
  }
}

// Singleton with a token getter that reads from module-level storage.
// Pages call useDashboardService() to get a token-aware instance.
let _tokenGetter: TokenGetter = () => null;

export function setDashboardToken(getter: TokenGetter): void {
  _tokenGetter = getter;
}

// The singleton used by all pages (token injected at runtime via setDashboardToken)
export const dashboardService = new DashboardService(() => _tokenGetter());
