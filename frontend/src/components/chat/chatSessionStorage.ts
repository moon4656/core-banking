import { ChatResponse } from "@/types/chat";

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
};

export type ChatSession = {
  id: string;
  title: string;
  messages: ConversationMessage[];
  lastResult: ChatResponse | null;
  createdAt: number;
  updatedAt: number;
};

function storageKey(userName: string) {
  return `core-banking-chat-sessions:${userName}`;
}

export function loadChatSessions(userName: string): ChatSession[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(storageKey(userName));
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw) as ChatSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveChatSessions(userName: string, sessions: ChatSession[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(storageKey(userName), JSON.stringify(sessions));
}

export function createChatSession(): ChatSession {
  const now = Date.now();

  return {
    id:
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `chat-${now}`,
    title: "새 대화",
    messages: [],
    lastResult: null,
    createdAt: now,
    updatedAt: now,
  };
}

export function buildSessionTitle(text: string) {
  const compact = text.trim().replace(/\s+/g, " ");
  if (!compact) {
    return "새 대화";
  }

  return compact.length > 26 ? `${compact.slice(0, 26)}...` : compact;
}
