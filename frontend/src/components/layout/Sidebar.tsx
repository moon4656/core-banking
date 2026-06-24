"use client";

import AccountTreeRoundedIcon from "@mui/icons-material/AccountTreeRounded";
import ApiRoundedIcon from "@mui/icons-material/ApiRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import ForumRoundedIcon from "@mui/icons-material/ForumRounded";
import HubRoundedIcon from "@mui/icons-material/HubRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import LabelRoundedIcon from "@mui/icons-material/LabelRounded";
import LinkRoundedIcon from "@mui/icons-material/LinkRounded";
import ListAltRoundedIcon from "@mui/icons-material/ListAltRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import ManageSearchRoundedIcon from "@mui/icons-material/ManageSearchRounded";
import FactCheckRoundedIcon from "@mui/icons-material/FactCheckRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import MonitorRoundedIcon from "@mui/icons-material/MonitorRounded";
import PrecisionManufacturingRoundedIcon from "@mui/icons-material/PrecisionManufacturingRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import SpeedRoundedIcon from "@mui/icons-material/SpeedRounded";
import StorageRoundedIcon from "@mui/icons-material/StorageRounded";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { startTransition, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { resetVerifiedSession } from "@/components/layout/sessionVerification";
import { clearStoredSession, getStoredSession, UserSession } from "@/lib/session";

const menus = [
  { label: "대시보드", href: "/dashboard", icon: <DashboardRoundedIcon /> },
  { label: "AI 상담", href: "/ai/chat", icon: <ForumRoundedIcon /> },
  { label: "기초정보 조회", href: "/inquiry/concepts", icon: <ListAltRoundedIcon /> },
  { label: "Trace 분석", href: "/analysis/traces", icon: <InsightsRoundedIcon /> },
  { label: "파이프라인 플로우", href: "/admin/pipeline", icon: <AccountTreeRoundedIcon /> },
  { label: "Decision Graph", href: "/admin/decisions", icon: <HubRoundedIcon /> },
  { label: "리더 평가", href: "/admin/leader-evaluations", icon: <ManageSearchRoundedIcon /> },
  { label: "Concept 탐지 평가", href: "/admin/concept-eval", icon: <FactCheckRoundedIcon /> },
  { label: "평가 이력", href: "/admin/concept-eval/history", icon: <HistoryRoundedIcon /> },
  { label: "실시간 모니터링", href: "/admin/monitoring", icon: <SpeedRoundedIcon /> },
  { label: "파이프라인 모니터", href: "/admin/leader-monitor", icon: <MonitorRoundedIcon /> },
  { label: "Concept 관리", href: "/admin/concepts", icon: <SettingsRoundedIcon /> },
  { label: "Alias 관리", href: "/admin/aliases", icon: <LabelRoundedIcon /> },
  { label: "Relation 관리", href: "/admin/relations", icon: <LinkRoundedIcon /> },
  { label: "Agent 매핑", href: "/admin/agent-mappings", icon: <HubRoundedIcon /> },
  { label: "API 매핑", href: "/admin/concept-api-mappings", icon: <ApiRoundedIcon /> },
  { label: "Agent Catalog", href: "/admin/agents", icon: <PrecisionManufacturingRoundedIcon /> },
  { label: "API Catalog", href: "/admin/apis", icon: <StorageRoundedIcon /> },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const [session, setSession] = useState<UserSession | null>(null);

  useEffect(() => {
    setPendingHref(null);
  }, [pathname]);

  useEffect(() => {
    setSession(getStoredSession());
  }, []);

  useEffect(() => {
    startTransition(() => {
      menus.forEach((menu) => {
        router.prefetch(menu.href);
      });
    });
  }, [router]);

  return (
    <Box
      sx={{
        width: { xs: 88, md: 280 },
        height: "100vh",
        px: { xs: 1.25, md: 1.75 },
        py: 2,
        display: "flex",
        flexDirection: "column",
        color: "#f3f4f6",
        backgroundColor: "#202123",
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <Box sx={{ px: { xs: 0.75, md: 1.25 }, mb: 2.5 }}>
        <Typography
          variant="subtitle1"
          sx={{ fontWeight: 700, color: "#f9fafb", display: { xs: "none", md: "block" } }}
        >
          Core Banking AI
        </Typography>
        <Typography
          sx={{
            mt: 0.5,
            color: "rgba(243,244,246,0.62)",
            fontSize: 13,
            display: { xs: "none", md: "block" },
          }}
        >
          Banking operations workspace
        </Typography>
      </Box>

      <List
        sx={{
          display: "grid",
          gap: 0.15,
          alignContent: "start",
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          pr: 0.25,
        }}
      >
        {menus.map((menu) => {
          const selected = pendingHref === menu.href || pathname.startsWith(menu.href);
          const pending = pendingHref === menu.href;

          return (
            <ListItemButton
              key={menu.href}
              selected={selected}
              onClick={() => {
                if (pathname.startsWith(menu.href)) {
                  return;
                }

                setPendingHref(menu.href);
                startTransition(() => {
                  router.push(menu.href);
                });
              }}
              sx={{
                height: 38,
                px: { xs: 0.75, md: 0.875 },
                py: 0,
                borderRadius: "8px",
                alignItems: "center",
                boxSizing: "border-box",
                color: "rgba(243,244,246,0.9)",
                "& .MuiListItemText-root": {
                  display: { xs: "none", md: "block" },
                },
                "& .MuiListItemText-primary": {
                  fontSize: 14,
                  lineHeight: 1.2,
                  fontWeight: 500,
                },
                "&.Mui-selected": {
                  backgroundColor: "rgba(255,255,255,0.09)",
                  color: "#ffffff",
                },
                "&.Mui-selected:hover": {
                  backgroundColor: "rgba(255,255,255,0.09)",
                },
                "&:hover": {
                  backgroundColor: "rgba(255,255,255,0.05)",
                },
              }}
            >
              <ListItemIcon
                sx={{
                  color: "inherit",
                  minWidth: { xs: 0, md: 30 },
                  justifyContent: "center",
                  "& .MuiSvgIcon-root": {
                    fontSize: 20,
                  },
                }}
              >
                {pending ? <CircularProgress size={18} color="inherit" /> : menu.icon}
              </ListItemIcon>
              <ListItemText primary={menu.label} />
            </ListItemButton>
          );
        })}
      </List>

      <Box
        sx={{
          mt: 2,
          p: { xs: 1.25, md: 1.5 },
          borderRadius: "18px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "rgba(255,255,255,0.04)",
        }}
      >
        <Typography
          variant="subtitle2"
          sx={{ mb: 1, display: { xs: "none", md: "block" }, color: "#f9fafb" }}
        >
          현재 세션
        </Typography>

        <Stack spacing={1}>
          <Typography sx={{ fontWeight: 600, display: { xs: "none", md: "block" } }}>
            {session?.name ?? "미로그인"}
          </Typography>

          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            sx={{ display: { xs: "none", md: "flex" } }}
          >
            {session ? (
              <Chip
                label={session.role}
                size="small"
                color="primary"
                variant="outlined"
                sx={{ color: "#f3f4f6", borderColor: "rgba(255,255,255,0.16)" }}
              />
            ) : null}
            {session ? (
              <Chip
                label={session.authMode}
                size="small"
                variant="outlined"
                sx={{ color: "#d1d5db", borderColor: "rgba(255,255,255,0.12)" }}
              />
            ) : null}
          </Stack>

          <Button
            fullWidth
            color="inherit"
            variant="outlined"
            startIcon={<LogoutRoundedIcon />}
            onClick={() => {
              resetVerifiedSession();
              clearStoredSession();
              router.push("/login");
            }}
            sx={{
              mt: 0.5,
              borderColor: "rgba(255,255,255,0.14)",
              color: "#f3f4f6",
              minWidth: 0,
              "&:hover": {
                borderColor: "rgba(255,255,255,0.24)",
                backgroundColor: "rgba(255,255,255,0.05)",
              },
              "& .MuiButton-startIcon": {
                mr: { xs: 0, md: 1 },
              },
            }}
          >
            <Box component="span" sx={{ display: { xs: "none", md: "inline" } }}>
              로그아웃
            </Box>
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}
