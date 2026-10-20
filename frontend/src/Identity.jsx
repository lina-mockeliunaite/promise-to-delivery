// The deal's identity in the top bar once its header card has scrolled out of view (20 Oct): name, stage pill, go-live.
// The header card itself is not sticky. Nothing here is printed.
import { useEffect, useState } from "react";
import { fmtDate } from "./format.js";
import { headerScrolledPast } from "./dealpage.js";

// [attach, past]: attach goes on the header card's ref; past is true while that card is scrolled up beneath the top bar.
export function useScrolledPast(topBar = 48) {
  const [el, setEl] = useState(null);
  const [past, setPast] = useState(false);
  useEffect(() => {
    if (!el || typeof IntersectionObserver === "undefined") return undefined;
    const io = new IntersectionObserver(
      ([e]) => setPast(headerScrolledPast(e.isIntersecting, e.boundingClientRect.bottom, e.rootBounds?.top ?? topBar)),
      { rootMargin: `-${topBar}px 0px 0px 0px`, threshold: 0 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [el, topBar]);
  return [setEl, past];
}

export function IdentityLine({ name, stage, goLive, show, className = "" }) {
  return (
    <span className={`dp-ident ${show ? "is-on" : ""} ${className}`} aria-hidden={!show}>
      <strong>{name}</strong>
      <span className="dp-ident-sep">·</span>
      <span className="dp-stage-pill dp-stage-pill-sm">{stage}</span>
      {goLive && <><span className="dp-ident-sep">·</span><span className="dp-ident-muted">Go-live {fmtDate(goLive)}</span></>}
    </span>
  );
}
