import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import { authService, type AuthUser } from '../services/authService';
import { setDashboardToken } from '../services/dashboardService';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ token: null, user: null });

  useEffect(() => {
    setDashboardToken(() => state.token);
  }, [state.token]);

  const login = useCallback(async (email: string, password: string) => {
    const { token, user } = await authService.login(email, password);
    setDashboardToken(() => token);
    setState({ token, user });
  }, []);

  const logout = useCallback(() => {
    setDashboardToken(() => null);
    setState({ token: null, user: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        isAuthenticated: state.token !== null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

/** Returns the stored Bearer token for use in service fetch calls. */
export function useToken(): string | null {
  return useAuth().token;
}
