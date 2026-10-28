// The landing page (20 Oct): shown on the first visit only. The product in one sentence, who it is for, and two sample scenarios,
// each with one concrete mismatch read from that deal's own stored data. No log-in (there are no accounts); uploading belongs to
// "+ New deal". The full deal list stays one click away.
import Logo from "./Logo.jsx";
import { useEffect, useState } from "react";
import * as api from "./api.js";
import { AUDIENCE_ITEMS, CARDS_LABEL, DESCRIPTION, FICTIONAL, SUBHEAD, TAGLINE } from "./brand.js";
import { MismatchSentence, TitleLine } from "./Drawer.jsx";
import { availableSamples, pickMismatches } from "./landing.js";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "./DealPage.css";
import "./Landing.css";

export default function Landing({ deals, unavailable = false, onOpen, onList }) {
  const samples = availableSamples(deals);
  const [registers, setRegisters] = useState({}); // deal -> its register; absent until it loads, and when it cannot be read
  const key = samples.map((s) => s.deal).join(",");
  useEffect(() => {
    let live = true;
    samples.forEach((s) => api.fetchRegister(s.deal).then((r) => live && setRegisters((f) => ({ ...f, [s.deal]: r })), () => {}));
    return () => { live = false; };
  }, [key]);
  // The cards are picked together, in card order, so they show different kinds of mismatch (see pickMismatches).
  const picks = pickMismatches(samples.map((s) => registers[s.deal] ?? null));
  const found = Object.fromEntries(samples.map((s, n) => [s.deal, picks[n]]));
  const cards = samples.filter((s) => found[s.deal]);
  return (
    <div className="dp land">
      <div className="land-inner">
        <section className="land-intro">
          <Logo height={36} />
          <h1>{TAGLINE}</h1>
          <p className="land-sub">{SUBHEAD.map((line) => <span key={line}>{line}</span>)}</p>
          <p className="land-desc">{DESCRIPTION}</p>
          <ul className="land-aud" aria-label="Who it is for">
            {AUDIENCE_ITEMS.map(([role, phrase]) => <li key={role}><strong>{role}</strong> {phrase}</li>)}
          </ul>
          <div className="land-actions">
            <button type="button" className="dp-link-btn dp-brand" onClick={onList}>See all deal reviews</button>
          </div>
          {unavailable && <p className="land-quiet" role="status">The sample deal can't be loaded right now. Check that the server is running.</p>}
        </section>
        {cards.length > 0 && (
          <div className="land-cards" aria-label="Two sample scenarios">
            <span className="dp-eyebrow land-cards-label">{CARDS_LABEL}</span>
            {cards.map((s) => (
              <article key={s.deal} className="dp-card land-example">
                <span className="dp-eyebrow">{s.title}</span>
                <span className="land-parties">{s.parties}</span>
                <TitleLine title={found[s.deal].title} labels={found[s.deal].badges} stacked />
                <MismatchSentence parts={found[s.deal].told} />
                <MismatchSentence parts={found[s.deal].parts} />
                <button type="button" className="dp-btn dp-btn-dark land-open" onClick={() => onOpen(s.deal)}>Open sample deal</button>
              </article>
            ))}
          </div>
        )}
      </div>
      <footer className="dp-foot">{FICTIONAL}</footer>
    </div>
  );
}
