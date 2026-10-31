import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { LogIn, UserPlus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Button } from "../components/Button";
import { Field, Input } from "../components/Field";
import { cn } from "../lib/cn";

type Seat = "seller" | "client";
type ClientMode = "signin" | "register";

export default function SignInPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [seat, setSeat] = useState<Seat>("seller");
  const [clientMode, setClientMode] = useState<ClientMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");

  const finish = () => {
    queryClient.invalidateQueries({ queryKey: ["session"] });
    navigate(seat === "seller" ? "/console" : "/briefs");
  };

  const sellerSignIn = useMutation({
    mutationFn: () => api.signIn(email, password),
    onSuccess: finish,
  });

  const clientAuth = useMutation({
    mutationFn: () =>
      clientMode === "register"
        ? api.registerClient({ email, password, display_name: displayName })
        : api.clientSignIn(email, password),
    onSuccess: finish,
  });

  const busy = sellerSignIn.isPending || clientAuth.isPending;
  const error =
    sellerSignIn.error instanceof ApiError
      ? sellerSignIn.error
      : clientAuth.error instanceof ApiError
        ? clientAuth.error
        : null;

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (seat === "seller") {
      sellerSignIn.mutate();
    } else {
      clientAuth.mutate();
    }
  };

  return (
    <div className="mx-auto grid max-w-[880px] gap-10 pt-6 lg:grid-cols-[1fr_0.9fr]">
      <div className="flex flex-col gap-4">
        <span className="label">Two seats, one desk</span>
        <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.03em]">
          The studio prices it. The client confirms it.
        </h1>
        <p className="max-w-[46ch] text-[14px] leading-relaxed text-ink-muted">
          Sign in as the studio to review briefs, price scopes against the published rules and issue
          quotes. Sign in as a client to submit a brief, pick a scope and pay the confirmed version.
        </p>
        <div className="mt-4 rounded-md border border-line bg-paper-card px-4 py-3">
          <span className="label">Demo accounts</span>
          <p className="mt-1 font-mono text-[12px] leading-relaxed text-ink-muted">
            studio · seller@scopebridge.local
            <br />
            client · client@scopebridge.local
            <br />
            password · set in your .env
          </p>
        </div>
      </div>

      <form
        onSubmit={submit}
        className="surface flex flex-col gap-4 px-5 py-6"
      >
        <div className="grid grid-cols-2 gap-1 rounded-md border border-line bg-paper-deep p-1">
          {(
            [
              ["seller", "Studio"],
              ["client", "Client"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setSeat(value)}
              className={cn(
                "cursor-pointer rounded-sm px-3 py-1.5 text-[13px] font-medium transition-colors duration-150",
                seat === value
                  ? "bg-pine text-paper"
                  : "text-ink-muted hover:text-ink",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {seat === "client" ? (
          <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            <button
              type="button"
              onClick={() => setClientMode("signin")}
              className={cn(
                "cursor-pointer underline-offset-4 hover:text-ink hover:underline",
                clientMode === "signin" && "text-pine underline",
              )}
            >
              sign in
            </button>
            <span className="h-3 w-px bg-line" />
            <button
              type="button"
              onClick={() => setClientMode("register")}
              className={cn(
                "cursor-pointer underline-offset-4 hover:text-ink hover:underline",
                clientMode === "register" && "text-pine underline",
              )}
            >
              create an account
            </button>
          </div>
        ) : null}

        {seat === "client" && clientMode === "register" ? (
          <Field label="Your name" htmlFor="account-name">
            <Input
              id="account-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Maya Ortiz"
              autoComplete="name"
            />
          </Field>
        ) : null}

        <Field label="Email" htmlFor="account-email">
          <Input
            id="account-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={seat === "seller" ? "seller@scopebridge.local" : "you@company.example"}
          />
        </Field>
        <Field label="Password" htmlFor="account-password">
          <Input
            id="account-password"
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

        <Button
          type="submit"
          busy={busy}
          icon={
            seat === "seller" || clientMode === "signin" ? (
              <LogIn size={15} />
            ) : (
              <UserPlus size={15} />
            )
          }
        >
          {seat === "seller"
            ? "Sign in to the studio"
            : clientMode === "signin"
              ? "Sign in as a client"
              : "Create account"}
        </Button>
        <p className="font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-ink-faint">
          Five failed attempts lock this email for 15 minutes.
        </p>
      </form>
    </div>
  );
}
