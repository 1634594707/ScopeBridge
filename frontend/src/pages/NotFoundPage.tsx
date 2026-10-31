import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { BrandMark } from "../components/BrandMark";
import { Button } from "../components/Button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[55vh] flex-col items-start justify-center gap-5">
      <BrandMark className="h-10 w-10 text-pine" />
      <span className="label">404 · not on the desk</span>
      <h1 className="max-w-[22ch] text-[32px] font-semibold leading-tight tracking-[-0.03em] text-ink">
        This page is outside the agreed scope.
      </h1>
      <p className="max-w-[52ch] text-[14px] leading-relaxed text-ink-muted">
        The address does not match any page. If you followed a link to a brief, it may have been
        deleted or belong to another account.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link to="/">
          <Button icon={<ArrowLeft size={15} />}>Back to the overview</Button>
        </Link>
        <Link to="/rules">
          <Button variant="secondary">Read the price list</Button>
        </Link>
      </div>
    </div>
  );
}
