import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Hero } from "./landing/Hero";
import { Lifecycle } from "./landing/Lifecycle";
import { Payments } from "./landing/Payments";
import { Pricing } from "./landing/Pricing";
import { Trust } from "./landing/Trust";
import { Walkthrough } from "./landing/Walkthrough";

/** The router does not scroll to `#section` links on its own; the landing page does it. */
function useHashScroll() {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) {
      return;
    }
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    target?.scrollIntoView({ block: "start" });
  }, [hash]);
}

export default function LandingPage() {
  useHashScroll();

  return (
    <div className="flex flex-col gap-24 pb-8 sm:gap-28">
      <Hero />
      <Walkthrough />
      <Lifecycle />
      <Pricing />
      <Payments />
      <Trust />
    </div>
  );
}
