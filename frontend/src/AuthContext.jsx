import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, setUnauthorizedHandler } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("sims_user")); } catch { return null; }
  });

  const clear = useCallback(() => { sessionStorage.clear(); setUser(null); }, []);
  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    clear();
  }, [clear]);

  useEffect(() => { setUnauthorizedHandler(clear); }, [clear]);

  // 30-minute session: the token expires server-side; also sign out in the UI
  useEffect(() => {
    if (!user) return undefined;
    const id = setInterval(() => {
      const exp = Number(sessionStorage.getItem("sims_exp"));
      if (exp && Date.now() > exp) clear();
    }, 15000);
    return () => clearInterval(id);
  }, [user, clear]);

  const login = async (username, password) => {
    const { data } = await api.post("/auth/login", { username, password });
    sessionStorage.setItem("sims_token", data.access_token);
    sessionStorage.setItem("sims_user", JSON.stringify(data.user));
    sessionStorage.setItem("sims_exp", String(Date.now() + data.expires_in * 1000));
    setUser(data.user);
  };
  const can = (perm) => !!user && user.permissions.includes(perm);

  return <Ctx.Provider value={{ user, login, logout, can }}>{children}</Ctx.Provider>;
}
