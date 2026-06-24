import Link from "next/link";
import { Box, Button, Stack, Typography } from "@mui/material";

import { PageCard } from "@/components/common/PageCard";
import { AppShell } from "@/components/layout/AppShell";

const quickMenus = [
  {
    title: "AI 상담",
    description: "FastAPI Chat API를 포털 안에서 바로 실행합니다.",
    href: "/ai/chat",
  },
  {
    title: "기준정보 조회",
    description: "개념과 별칭을 업무별로 검색하고 조회합니다.",
    href: "/inquiry/concepts",
  },
  {
    title: "Trace 분석",
    description: "request_id 기준으로 trace, event, evidence를 분석합니다.",
    href: "/analysis/traces",
  },
  {
    title: "리더 평가",
    description: "리더 Agent의 intent, concept, agent 선택과 근거 품질을 점검합니다.",
    href: "/admin/leader-evaluations",
  },
  {
    title: "기준정보 관리",
    description: "관리자 관점에서 기준정보 CRUD와 운영 구성을 확인합니다.",
    href: "/admin/concepts",
  },
];

export default function DashboardPage() {
  return (
    <AppShell title="대시보드">
      <Stack spacing={2.5}>
        <PageCard
          title="1차 포털 범위"
          subtitle="기존 정적 채팅 UI를 메뉴형 포털 구조로 확장하는 첫 단계입니다."
        >
          <Typography>
            현재 단계에서는 AI 상담, 기준정보 조회, Trace 분석, 리더 평가, 관리자 확장 화면을
            하나의 포털 안에서 통합합니다.
          </Typography>
        </PageCard>

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          }}
        >
          {quickMenus.map((menu) => (
            <PageCard key={menu.href} title={menu.title} subtitle={menu.description}>
              <Button component={Link} href={menu.href} variant="contained">
                이동
              </Button>
            </PageCard>
          ))}
        </Box>
      </Stack>
    </AppShell>
  );
}
