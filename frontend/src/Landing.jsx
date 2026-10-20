// The landing page (20 Oct): shown on the first visit only. The product in one sentence, who it is for, one concrete mismatch
// from the sample deal's stored data, and the way in. No log-in (there are no accounts); uploading belongs to "+ New deal".
import { useEffect, useState } from "react";
import * as api from "./api.js";
import { AUDIENCE, DESCRIPTION, FICTIONAL, NAME, TAGLINE } from "./brand.js";
import { MismatchSentence } from "./Drawer.jsx";
import { SAMPLE_DEAL, pickMismatch } from "./landing.js";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "./DealPage.css";
import "./Landing.css";

export default function Landing({ hasSample, onSample, onList }) {
  const [mismatch, setMismatch] = useState(null);
  useEffect(() => {
    if (!hasSample) return undefined;
    let live = true;
    api.fetchRegister(SAMPLE_DEAL).then((r) => live && setMismatch(pickMismatch(r)), () => {});
    return () => { live = false; };
  }, [hasSample]);
  return (
    <div className="dp land">
      <div className="land-inner">
        <section className="land-intro">
          <span className="dp-wordmark">{NAME}</span>
          <h1>{TAGLINE}</h1>
          <p className="land-desc">{DESCRIPTION}</p>
          <p className="land-aud">{AUDIENCE}</p>
          <div className="land-actions">
            {hasSample && <button type="button" className="dp-btn dp-btn-dark land-primary" onClick={onSample}>Open a sample deal</button>}
            <button type="button" className="dp-link-btn dp-brand" onClick={onList}>See all deal reviews</button>
          </div>
        </section>
        {mismatch && (
          <aside className="dp-card land-example" aria-label="An example from the sample deal">
            <span className="dp-eyebrow">One commitment from the sample deal</span>
            <span className="dp-prow-title">{mismatch.title}</span>
            <MismatchSentence parts={mismatch.parts} />
          </aside>
        )}
      </div>
      <footer className="dp-foot">{FICTIONAL}</footer>
    </div>
  );
}
