"use client";

import { Card, CardContent, Typography } from "@mui/material";
import { ReactNode } from "react";

export function PageCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <Card
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "24px",
        backgroundColor: "background.paper",
        boxShadow: "0 1px 2px rgba(17, 24, 39, 0.04)",
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
        <Typography variant="h6">{title}</Typography>
        {subtitle ? (
          <Typography color="text.secondary" sx={{ mt: 0.75, mb: 2 }}>
            {subtitle}
          </Typography>
        ) : null}
        {children}
      </CardContent>
    </Card>
  );
}
