import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Button } from "../components/Button";
import { Field, Input } from "../components/Field";

export default function SignInPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const signIn = useMutation({
    mutationFn: () => api.signIn(email, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["session"] });
      navigate("/console");
    },
  });

  const error = signIn.error instanceof ApiError ? signIn.error : null;

  return (
    <div className="mx-auto grid max-w-[880px] gap-10 pt-6 lg:grid-cols-[1fr_0.9fr]">
      <div className="flex flex-col gap-4">
        <span className="label">Seller access</span>
        <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.03em]">
          The contract desk, behind one password.
        </h1>
        <p className="max-w-[46ch] text-[14px] leading-relaxed text-ink-muted">
          One operator account manages every brief. Clients never sign in — they hold a private link
          scoped to a single request.
        </p>
        <div className="mt-4 rounded-md border border-line bg-paper-card px-4 py-3">
          <span className="label">Demo account</span>
          <p className="mt-1 font-mono text-[12px] leading-relaxed text-ink-muted">
            seller@scopebridge.local
            <br />
            ScopeBridge-2026-demo
          </p>
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          signIn.mutate();
        }}
        className="surface flex flex-col gap-4 px-5 py-6"
      >
        <Field label="Email" htmlFor="seller-email">
          <Input
            id="seller-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="seller@scopebridge.local"
          />
        </Field>
        <Field label="Password" htmlFor="seller-password">
          <Input
            id="seller-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••••••"
          />
        </Field>

        {error ? (
          <p className="rounded-md border border-flag-bad/30 bg-flag-bad/5 px-3 py-2 text-[12px] text-flag-bad">
            {error.message}
          </p>
        ) : null}

        <Button type="submit" busy={signIn.isPending} icon={<LogIn size={15} />}>
          Sign in
        </Button>
        <p className="font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-ink-faint">
          Five failed attempts lock this email for 15 minutes.
        </p>
      </form>
    </div>
  );
}
