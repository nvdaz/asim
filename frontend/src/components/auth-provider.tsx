import { createContext, useContext, useState } from "react";

type User = {
  name: string;
};

type Auth = {
  token: string;
  user: User;
};

type AuthProviderState = {
  auth: Auth | null;
  setAuth: (auth: Auth) => void;
};

const initialState: AuthProviderState = {
  auth: null,
  setAuth: () => null,
};

export const AuthProviderContext =
  createContext<AuthProviderState>(initialState);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<Auth | null>(() => {
    const auth = localStorage.getItem("auth");
    try {
      return auth ? JSON.parse(auth) : null;
    } catch {
      return null;
    }
  });

  const value = {
    auth,
    setAuth: (auth: Auth) => {
      localStorage.setItem("auth", JSON.stringify(auth));
      setAuth(auth);
    },
  };

  return (
    <AuthProviderContext.Provider value={value}>
      {children}
    </AuthProviderContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthProviderContext);

  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  const token = ctx.auth?.token;
  const user = ctx.auth?.user;
  const setAuth = ctx.setAuth;

  return { token, user, setAuth };
}
