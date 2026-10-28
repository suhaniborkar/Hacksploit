// Auth service — handles login/logout HTTP calls to the backend.
// Token is never written to localStorage; it lives only in AuthContext memory.

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
}

const BASE = '/api/v1';

export const authService = {
  async login(email: string, password: string): Promise<{ token: string; user: AuthUser }> {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as { detail?: string }).detail || 'Invalid credentials');
    }

    const data: LoginResponse = await res.json();

    // Immediately fetch the /me profile so we have name+role available
    const meRes = await fetch(`${BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });

    if (!meRes.ok) {
      throw new Error('Could not fetch user profile after login');
    }

    const me: AuthUser = await meRes.json();
    return { token: data.access_token, user: me };
  },
};
