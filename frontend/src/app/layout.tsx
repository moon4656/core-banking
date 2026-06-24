import type { Metadata } from "next";
import { ReactNode } from "react";

import { Providers } from "@/lib/providers";

export const metadata: Metadata = {
  title: "Core Banking Portal",
  description: "AI 상담, 조회, 분석, 관리자 화면 통합 포털",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
