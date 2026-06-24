"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { primeVerifiedSession, resetVerifiedSession } from "@/components/layout/sessionVerification";
import { ApiError, authLogin } from "@/lib/api";
import { setStoredSession } from "@/lib/session";

const schema = z.object({
  name: z.string().min(1, "Please enter a user name."),
  apiKey: z.string().min(1, "Please enter the X-API-Key value."),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { control, handleSubmit, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "portal-user",
      apiKey: "",
    },
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("reason") === "expired") {
      setError("Session expired. Please sign in again.");
    }
  }, []);

  async function onSubmit(values: FormValues) {
    setMessage(null);
    setError(null);

    try {
      const session = await authLogin(values.name, values.apiKey);
      resetVerifiedSession();
      primeVerifiedSession(session);
      setStoredSession({
        name: session.name,
        role: session.role,
        accessToken: session.access_token,
        authMode: session.auth_mode,
        tokenType: session.token_type,
      });
      setMessage(`Signed in as ${session.role}`);
      router.push("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Login failed.");
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 2,
        background:
          "radial-gradient(circle at top left, #dcecff 0%, #eef4fb 45%, #f8fbff 100%)",
      }}
    >
      <Card sx={{ width: "100%", maxWidth: 460, borderRadius: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h4">Operations Portal Login</Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                The server validates the X-API-Key and determines the role.
              </Typography>
            </Box>

            {message ? <Alert severity="success">{message}</Alert> : null}
            {error ? <Alert severity="error">{error}</Alert> : null}

            <Controller
              name="name"
              control={control}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="User Name"
                  error={!!fieldState.error}
                  helperText={fieldState.error?.message}
                />
              )}
            />

            <Controller
              name="apiKey"
              control={control}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="X-API-Key"
                  type="password"
                  error={!!fieldState.error}
                  helperText={
                    fieldState.error?.message ?? "The server checks whether the key is valid."
                  }
                />
              )}
            />

            <Button
              variant="contained"
              size="large"
              onClick={handleSubmit(onSubmit)}
              disabled={formState.isSubmitting}
            >
              Sign In
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
