import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useSession } from "./hooks/useSession";
import { ApiError } from "./lib/api";
import type { AccountRole } from "./lib/types";
import LandingPage from "./pages/LandingPage";
import StartPage from "./pages/StartPage";
import SignInPage from "./pages/SignInPage";
import PayPage from "./pages/PayPage";
import PortalPage from "./pages/PortalPage";
import BriefsPage from "./pages/BriefsPage";
import ConsolePage from "./pages/ConsolePage";
import RequirementPage from "./pages/RequirementPage";
import QuotePage from "./pages/QuotePage";
import RulesPage from "./pages/RulesPage";
import NotFoundPage from "./pages/NotFoundPage";

function PublicLayout() {
  return (
    <AppShell variant="public">
      <Outlet />
    </AppShell>
  );
}

function RoleLayout({
  role,
  variant,
  fallback,
  errorCopy,
}: {
  role: AccountRole;
  variant: "seller" | "client";
  fallback: string;
  errorCopy: string;
}) {
  const session = useSession();
  const status = session.error instanceof ApiError ? session.error.status : 0;

  // While the session is unknown render a neutral spinner in the public shell;
  // 401 means "not signed in" and goes to the sign-in page; a signed-in account
  // of the other role is sent to its own home. Only the matching role mounts
  // this shell.
  if (session.isLoading) {
    return (
      <AppShell variant="public">
        <div className="flex min-h-[50vh] items-center justify-center">
          <span className="h-4 w-4 animate-spin rounded-full border border-pine border-t-transparent" />
        </div>
      </AppShell>
    );
  }
  if (status === 401) {
    return <Navigate to="/signin" replace />;
  }
  if (session.error) {
    return (
      <AppShell variant="public">
        <div className="mx-auto max-w-md py-20 text-sm text-flag-bad">{errorCopy}</div>
      </AppShell>
    );
  }
  if (session.data?.account.role !== role) {
    return <Navigate to={fallback} replace />;
  }
  return (
    <AppShell variant={variant}>
      <Outlet />
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      <Route
        element={
          <RoleLayout
            role="CLIENT"
            variant="client"
            fallback="/console"
            errorCopy="Your briefs could not be loaded. Check that the API is running."
          />
        }
      >
        <Route path="/start" element={<StartPage />} />
        <Route path="/briefs" element={<BriefsPage />} />
        <Route path="/briefs/:id" element={<PortalPage />} />
        <Route path="/pay/:paymentId" element={<PayPage />} />
      </Route>
      <Route
        element={
          <RoleLayout
            role="SELLER"
            variant="seller"
            fallback="/briefs"
            errorCopy="The seller console could not be loaded. Check that the API is running."
          />
        }
      >
        <Route path="/console" element={<ConsolePage />} />
        <Route path="/requirements/:id" element={<RequirementPage />} />
        <Route path="/quotes/:id" element={<QuotePage />} />
      </Route>
    </Routes>
  );
}
