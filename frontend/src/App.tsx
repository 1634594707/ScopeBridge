import { Outlet, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { RequireSeller } from "./hooks/useSession";
import LandingPage from "./pages/LandingPage";
import StartPage from "./pages/StartPage";
import SignInPage from "./pages/SignInPage";
import PortalPage from "./pages/PortalPage";
import ConsolePage from "./pages/ConsolePage";
import RequirementPage from "./pages/RequirementPage";
import QuotePage from "./pages/QuotePage";
import RulesPage from "./pages/RulesPage";

function PublicLayout() {
  return (
    <AppShell variant="public">
      <Outlet />
    </AppShell>
  );
}

function SellerLayout() {
  return (
    <AppShell variant="seller">
      <RequireSeller />
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/start" element={<StartPage />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/r/:token" element={<PortalPage />} />
        <Route path="/rules" element={<RulesPage />} />
      </Route>
      <Route element={<SellerLayout />}>
        <Route path="/console" element={<ConsolePage />} />
        <Route path="/requirements/:id" element={<RequirementPage />} />
        <Route path="/quotes/:id" element={<QuotePage />} />
      </Route>
    </Routes>
  );
}
