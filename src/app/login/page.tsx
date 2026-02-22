"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Shield, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";

const LOGIN_TIMEOUT_MS = 15000;

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { login, loginError, clearLoginError } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearLoginError();
    setSubmitError(null);
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    if (!trimmedEmail || !trimmedPassword) {
      return; // validation message shown below
    }
    setIsSubmitting(true);
    try {
      const ok = await Promise.race([
        login(trimmedEmail, trimmedPassword),
        new Promise<boolean>((_, reject) =>
          setTimeout(
            () => reject(new Error("Connection timed out. Check that the backend is running.")),
            LOGIN_TIMEOUT_MS
          )
        ),
      ]);
      if (!ok) setIsSubmitting(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed. Please try again.";
      setSubmitError(msg);
      setIsSubmitting(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = email.trim().length > 0 && password.trim().length > 0;
  const showRequiredError = email.length > 0 || password.length > 0;
  const missingFields: string[] = [];
  if (showRequiredError && !email.trim()) missingFields.push("Email");
  if (showRequiredError && !password.trim()) missingFields.push("Password");

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-12">
      <div className="absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(163,126,59,0.16),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_60%,rgba(197,160,89,0.08),transparent_50%)]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="w-full max-w-[420px]"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.05, ease: "easeOut" }}
          className="relative rounded-2xl p-[1px] shadow-2xl"
          style={{
            background:
              "linear-gradient(135deg, rgba(163,126,59,0.28) 0%, rgba(197,160,89,0.18) 100%)",
          }}
        >
          <div className="rounded-2xl bg-card/70 p-8 shadow-xl backdrop-blur-2xl dark:bg-card/80">
            <div className="flex flex-col items-center gap-5 text-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1, duration: 0.25 }}
                className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/20"
              >
                <Shield className="h-7 w-7 text-white" />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.25 }}
              >
                <h1 className="text-2xl font-bold tracking-tight">Sign in</h1>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  AI Compliance Intelligence Platform
                </p>
              </motion.div>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              {(submitError || loginError || missingFields.length > 0) && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {submitError || loginError || (missingFields.length > 0 ? `${missingFields.join(" and ")} required` : null)}
                </div>
              )}
              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 rounded-lg border-border/80 bg-background text-foreground focus-visible:ring-2 focus-visible:ring-primary/50"
                />
              </div>
              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 rounded-lg border-border/80 bg-background pr-11 text-foreground focus-visible:ring-2 focus-visible:ring-primary/50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((p) => !p)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
              <div className="rounded-lg border border-primary/30 bg-primary/5 px-3 py-2.5">
                <p className="text-xs font-medium text-foreground leading-relaxed">
                  Use the email and password from your admin to sign in.
                </p>
              </div>
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.25 }}
              >
                <Button
                  type="submit"
                  variant="gradient"
                  className="h-11 w-full rounded-lg font-medium transition-all duration-200 hover:opacity-95 active:scale-[0.99]"
                  disabled={isSubmitting || !canSubmit}
                >
                  {isSubmitting ? "Signing in…" : "Sign in"}
                </Button>
              </motion.div>
            </form>
          </div>
        </motion.div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          <Link href="/" className="underline hover:text-foreground" prefetch>
            Back to home
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
