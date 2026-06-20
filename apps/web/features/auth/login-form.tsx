"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import type { AuthLoginResponse } from "@gridtrace/contracts";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from "@gridtrace/ui";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Zap } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/client";
import { ROLE_HOME, resolveRole } from "@/lib/roles";

const loginSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const { client } = useApi();
  const { login, user, ready } = useAuth();
  const [error, setError] = useState<string | null>(null);

  // Already signed in? Skip the login screen, landing on the role's home.
  useEffect(() => {
    if (ready && user) router.replace(ROLE_HOME[user.role]);
  }, [ready, user, router]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "demo_operator", password: "SuperSecret123!" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      const res = await client.request<AuthLoginResponse>("api/v1/auth/login", {
        method: "POST",
        body: values,
      });
      const role = resolveRole(res.user.role);
      login({ id: res.user.id, name: res.user.name, role }, res.access_token);
      router.replace(ROLE_HOME[role]);
    } catch {
      setError("Sign-in failed. Check your credentials and try again.");
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-sm bg-primary text-primary-foreground">
            <Zap className="h-5 w-5" />
          </div>
          <CardTitle>Sign in to GridTrace</CardTitle>
          <CardDescription>
            Find where energy disappears, explain why, and prioritize what to inspect.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input id="username" type="text" autoComplete="username" {...register("username")} />
              {errors.username ? (
                <p className="text-xs text-danger">{errors.username.message}</p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
              />
              {errors.password ? (
                <p className="text-xs text-danger">{errors.password.message}</p>
              ) : null}
            </div>
            {error ? <p className="text-sm text-danger">{error}</p> : null}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
            <p className="text-center text-xs text-muted-foreground">
              Demo: operator · analyst · inspector (password 8+ chars)
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
