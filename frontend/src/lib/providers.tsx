"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { ReactNode, useState } from "react";

import { createAppQueryClient } from "@/lib/query-client";
import { theme } from "@/lib/theme";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => createAppQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
