import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, getToken, setToken, onUnauthorized } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCurrentUser(); }, [loadCurrentUser]);

  useEffect(() => {
    // Any 401 from any API call (expired/invalid token) logs the user out
    // globally, rather than each page having to handle it separately.
    return onUnauthorized(() => {
      setToken(null);
      setUser(null);
    });
  }, []);

  const login = async (email, password) => {
    const res = await authApi.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const signup = async (email, password, name) => {
    const res = await authApi.signup(email, password, name);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
