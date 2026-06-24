"use client";

import { Box, Link, Typography } from "@mui/material";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { normalizeMarkdown } from "./normalizeMarkdown";

export function MarkdownMessage({ content }: { content: string }) {
  const normalizedContent = normalizeMarkdown(content);

  return (
    <Box
      sx={{
        lineHeight: 1.7,
        overflowWrap: "anywhere",
        color: "#1f2937",
        "& > :first-of-type": { mt: 0 },
        "& > :last-child": { mb: 0 },
        "& ul, & ol": {
          marginTop: 0.3,
          marginBottom: 0.3,
        },
        "& li > p": {
          margin: 0,
        },
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <Typography variant="h5" sx={{ mt: 0.5, mb: 1.5 }}>
              {children}
            </Typography>
          ),
          h2: ({ children }) => (
            <Typography variant="h6" sx={{ mt: 0.4, mb: 1.2 }}>
              {children}
            </Typography>
          ),
          h3: ({ children }) => (
            <Typography variant="subtitle1" sx={{ mt: 1.25, mb: 0.55, fontWeight: 700 }}>
              {children}
            </Typography>
          ),
          h4: ({ children }) => (
            <Typography variant="body1" sx={{ mt: 1, mb: 0.35, fontWeight: 700 }}>
              {children}
            </Typography>
          ),
          p: ({ children }) => (
            <Typography sx={{ mb: 0.8, whiteSpace: "pre-wrap", color: "inherit" }}>
              {children}
            </Typography>
          ),
          blockquote: ({ children }) => (
            <Box
              component="blockquote"
              sx={{
                my: 1.5,
                mx: 0,
                pl: 1.5,
                py: 0.1,
                borderLeft: "3px solid #d1d5db",
                color: "#4b5563",
              }}
            >
              {children}
            </Box>
          ),
          ul: ({ children }) => (
            <Box component="ul" sx={{ pl: 2.1, my: 0.1 }}>
              {children}
            </Box>
          ),
          ol: ({ children }) => (
            <Box component="ol" sx={{ pl: 2.1, my: 0.1 }}>
              {children}
            </Box>
          ),
          li: ({ children }) => (
            <Box component="li" sx={{ mb: 0.08 }}>
              <Typography component="span" sx={{ whiteSpace: "pre-wrap" }}>
                {children}
              </Typography>
            </Box>
          ),
          strong: ({ children }) => (
            <Box component="strong" sx={{ fontWeight: 700 }}>
              {children}
            </Box>
          ),
          a: ({ href, children }) => (
            <Link href={href} target="_blank" rel="noreferrer">
              {children}
            </Link>
          ),
          code: ({ children }) => (
            <Box
              component="code"
              sx={{
                px: 0.65,
                py: 0.2,
                borderRadius: 1,
                fontFamily: '"JetBrains Mono", Consolas, monospace',
                fontSize: "0.9em",
                backgroundColor: "#f3f4f6",
              }}
            >
              {children}
            </Box>
          ),
          table: ({ children }) => (
            <Box sx={{ overflowX: "auto", my: 1.5 }}>
              <Box
                component="table"
                sx={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: "0.875rem",
                  lineHeight: 1.6,
                }}
              >
                {children}
              </Box>
            </Box>
          ),
          thead: ({ children }) => (
            <Box component="thead" sx={{ backgroundColor: "#f3f4f6" }}>
              {children}
            </Box>
          ),
          tbody: ({ children }) => (
            <Box component="tbody">{children}</Box>
          ),
          tr: ({ children }) => (
            <Box
              component="tr"
              sx={{
                borderBottom: "1px solid #e5e7eb",
                "&:last-child": { borderBottom: "none" },
                "&:hover": { backgroundColor: "#f9fafb" },
              }}
            >
              {children}
            </Box>
          ),
          th: ({ children }) => (
            <Box
              component="th"
              sx={{
                px: 1.5,
                py: 0.85,
                textAlign: "left",
                fontWeight: 700,
                color: "#374151",
                borderBottom: "2px solid #d1d5db",
                whiteSpace: "nowrap",
              }}
            >
              {children}
            </Box>
          ),
          td: ({ children }) => (
            <Box
              component="td"
              sx={{
                px: 1.5,
                py: 0.75,
                color: "#1f2937",
                verticalAlign: "top",
              }}
            >
              {children}
            </Box>
          ),
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </Box>
  );
}
