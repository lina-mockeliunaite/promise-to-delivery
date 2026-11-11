// "Reset demo" in the deal-list footer (10 Nov): a grey link, then an inline confirm in the page (not a browser dialog).
import { useState } from "react";
import * as api from "./api.js";
import { RESET_IDLE, RESET_QUESTION, resetNext, runReset } from "./deals.js";
import { RESET_QUESTION_PUBLIC, useDemo } from "./demo.js";

const browser = { setHash: (h) => { window.location.hash = h; }, reload: () => window.location.reload() };

// variant "bar": the demo bar's own "Reset demo" (11 Nov); the confirm then opens as a panel under the bar. The same confirm, the same call, the same reload.
export default function ResetDemo({ resetApi = api.resetDemo, nav = browser, initial = RESET_IDLE, variant = "footer" }) {
  const [state, setState] = useState(initial);
  const demo = useDemo();
  const go = async () => {
    setState((s) => resetNext(s, "run"));
    const done = await runReset(resetApi, nav);
    if (!done.ok) setState((s) => resetNext(s, "fail", done.message));
  };
  if (state.step === "idle") {
    return <button type="button" className={variant === "bar" ? "demo-bar-link" : "dl-about dl-reset-link"} onClick={() => setState((s) => resetNext(s, "ask"))}>Reset demo</button>;
  }
  return (
    <div className={variant === "bar" ? "dl-reset demo-bar-reset" : "dl-reset"} role="group" aria-label="Reset demo">
      <p>{demo.public ? RESET_QUESTION_PUBLIC : RESET_QUESTION}</p>
      {state.message && <p className="dl-reset-error" role="alert">{state.message}</p>}
      <div className="dl-reset-actions">
        <button type="button" className="dl-btn" disabled={state.step === "busy"} onClick={go}>{state.step === "busy" ? "Resetting…" : "Reset"}</button>
        <button type="button" className="dl-btn" disabled={state.step === "busy"} onClick={() => setState((s) => resetNext(s, "cancel"))}>Cancel</button>
      </div>
    </div>
  );
}
