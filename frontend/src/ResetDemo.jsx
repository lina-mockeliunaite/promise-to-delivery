// "Reset demo" in the deal-list footer (10 Nov): a grey link, then an inline confirm in the page (not a browser dialog).
import { useState } from "react";
import * as api from "./api.js";
import { RESET_IDLE, RESET_QUESTION, resetNext, runReset } from "./deals.js";

const browser = { setHash: (h) => { window.location.hash = h; }, reload: () => window.location.reload() };

export default function ResetDemo({ resetApi = api.resetDemo, nav = browser, initial = RESET_IDLE }) {
  const [state, setState] = useState(initial);
  const go = async () => {
    setState((s) => resetNext(s, "run"));
    const done = await runReset(resetApi, nav);
    if (!done.ok) setState((s) => resetNext(s, "fail", done.message));
  };
  if (state.step === "idle") {
    return <button type="button" className="dl-about dl-reset-link" onClick={() => setState((s) => resetNext(s, "ask"))}>Reset demo</button>;
  }
  return (
    <div className="dl-reset" role="group" aria-label="Reset demo">
      <p>{RESET_QUESTION}</p>
      {state.message && <p className="dl-reset-error" role="alert">{state.message}</p>}
      <div className="dl-reset-actions">
        <button type="button" className="dl-btn" disabled={state.step === "busy"} onClick={go}>{state.step === "busy" ? "Resetting…" : "Reset"}</button>
        <button type="button" className="dl-btn" disabled={state.step === "busy"} onClick={() => setState((s) => resetNext(s, "cancel"))}>Cancel</button>
      </div>
    </div>
  );
}
