import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { AppShell } from "@/components/layout/AppShell";

export default function ChatPage() {
  return (
    <AppShell title="AI 상담">
      <ChatWorkspace />
    </AppShell>
  );
}
