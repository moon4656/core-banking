export type AppRole = "READONLY" | "ANALYST" | "ADMIN";

export type UserSession = {
  name: string;
  role: AppRole;
  accessToken: string;
  authMode: string;
  tokenType: string;
};

const STORAGE_KEY = "core-banking-session";

export function getStoredSession(): UserSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserSession;
  } catch {
    return null;
  }
}

export function setStoredSession(session: UserSession) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(STORAGE_KEY);
}
