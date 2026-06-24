import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    primary: {
      main: "#2563eb",
      dark: "#1d4ed8",
      light: "#dbeafe",
    },
    secondary: {
      main: "#0f766e",
    },
    background: {
      default: "#f7f7f8",
      paper: "#ffffff",
    },
    text: {
      primary: "#111827",
      secondary: "#6b7280",
    },
    divider: "#e5e7eb",
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: "\"Segoe UI\", \"Noto Sans KR\", sans-serif",
    h4: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h5: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    h6: {
      fontWeight: 700,
    },
    subtitle1: {
      fontWeight: 600,
    },
  },
});
