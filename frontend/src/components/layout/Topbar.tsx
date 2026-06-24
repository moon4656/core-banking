"use client";

import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { resetVerifiedSession } from "@/components/layout/sessionVerification";
import { clearStoredSession, getStoredSession, UserSession } from "@/lib/session";

export function Topbar({ title }: { title: string }) {
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);

  useEffect(() => {
    setSession(getStoredSession());
  }, []);

  return (
    <Box
      sx={{
        px: { xs: 2, md: 3 },
        py: 1.5,
        borderBottom: "1px solid",
        borderColor: "divider",
        backgroundColor: "rgba(255,255,255,0.82)",
        backdropFilter: "blur(10px)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", md: "center" }}
        spacing={1.5}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.25, fontSize: 13 }}>
            AI guidance, trace evidence, and operational context
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          {session ? (
            <Chip size="small" label={session.role} color="primary" variant="outlined" />
          ) : null}
          {session ? <Chip size="small" label={session.authMode} variant="outlined" /> : null}
          <Typography color="text.secondary" sx={{ fontSize: 14 }}>
            {session?.name ?? "미로그인"}
          </Typography>
          <Button
            color="inherit"
            size="small"
            startIcon={<LogoutRoundedIcon />}
            onClick={() => {
              resetVerifiedSession();
              clearStoredSession();
              router.push("/login");
            }}
          >
            로그아웃
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}
