import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getMe, login as apiLogin, register as apiRegister } from '../api/auth';
import { getToken, setToken as saveToken, clearTokens } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setTokenState] = useState(() => getToken());
  const [loading, setLoading] = useState(true);

  const fetchCurrentUser = useCallback(async () => {
    const activeToken = getToken();
    if (!activeToken) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await getMe();
      setUser(res.data);
    } catch (err) {
      console.error('Failed to load user profile', err);
      clearTokens();
      setUser(null);
      setTokenState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const login = async (email, password, rememberMe = true) => {
    const res = await apiLogin(email, password);
    const { access_token, user: userData } = res.data;
    if (access_token) {
      saveToken(access_token, rememberMe);
      setTokenState(access_token);
    }
    if (userData) {
      setUser(userData);
      return userData;
    }
    try {
      const meRes = await getMe();
      setUser(meRes.data);
      return meRes.data;
    } catch {
      return null;
    }
  };

  const register = async (name, email, password, rememberMe = true) => {
    const res = await apiRegister(name, email, password);
    const { access_token, user: userData } = res.data;
    if (access_token) {
      saveToken(access_token, rememberMe);
      setTokenState(access_token);
    }
    if (userData) {
      setUser(userData);
      return userData;
    }
    if (res.data.id && res.data.name) {
      const u = {
        id: res.data.id,
        name: res.data.name,
        email: res.data.email,
        preferences: res.data.preferences || {},
      };
      setUser(u);
      return u;
    }
    try {
      const meRes = await getMe();
      setUser(meRes.data);
      return meRes.data;
    } catch {
      return null;
    }
  };

  const logout = () => {
    clearTokens();
    setTokenState(null);
    setUser(null);
    window.location.href = '/login';
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
