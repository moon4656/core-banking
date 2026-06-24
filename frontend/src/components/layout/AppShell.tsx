"use client";

import { Box, CircularProgress } from "@mui/material";
import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/Sidebar";
import {
  getVerifiedSession,
  hasVerifiedSession,
  resetVerifiedSession,
} from "@/components/layout/sessionVerification";
import { Topbar } from "@/components/layout/Topbar";
import { apiGet, AuthSessionResponse } from "@/lib/api";
import { clearStoredSession, getStoredSession, setStoredSession } from "@/lib/session";

export function AppShell({
  title,
  children,
  noPadding = false,
}: {
  title: string;
  children: ReactNode;
  noPadding?: boolean;
}) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    async function verifySession() {
      const session = getStoredSession();
      if (!session) {
        resetVerifiedSession();
        clearStoredSession();
        router.replace("/login");
        return;
      }

      if (hasVerifiedSession()) {
        setReady(true);
        return;
      }

      try {
        const profile = await getVerifiedSession(() =>
          apiGet<AuthSessionResponse>("/api/v1/auth/me")
        );
        setStoredSession({
          name: profile.name,
          role: profile.role,
          accessToken: profile.access_token,
          authMode: profile.auth_mode,
          tokenType: profile.token_type,
        });
        setReady(true);
      } catch {
        resetVerifiedSession();
        clearStoredSession();
        router.replace("/login?reason=expired");
      }
    }

    void verifySession();
  }, [router]);

  if (!ready) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          backgroundColor: "background.default",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        height: "100vh",
        overflow: "hidden",
        backgroundColor: "#f7f7f8",
      }}
    >
      <Sidebar />
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <Topbar title={title} />
        <Box
          component="main"
          sx={{
            flex: 1,
            minHeight: 0,
            overflow: noPadding ? "hidden" : undefined,
            overflowY: noPadding ? undefined : "auto",
            ...(noPadding ? {} : { px: { xs: 2, md: 3 }, py: { xs: 2, md: 2.5 } }),
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
