// The "About this prototype" panel (19 Nov): pure helpers, so they are tested without a browser (the same way as resetNext in ResetDemo.jsx).
import { ABOUT_SCOPE, ABOUT_SETUP, ABOUT_SHOWS, ABOUT_VERSION, ABOUT_WHAT, DESCRIPTION } from "./brand.js";

// The panel is open or closed. "open" opens it; the close button, Esc and a click outside close it; anything else leaves it as it is.
export function aboutNext(open, action) {
  if (action === "open") return true;
  if (action === "button" || action === "escape" || action === "overlay") return false;
  return open;
}

// The action a key press means while the panel is open (null: none).
export const aboutKeyAction = (e) => (e && e.key === "Escape" ? "escape" : null);

// What the panel shows, in order. The description sentence comes first; "How the demo is set up" is in public mode only; the other sections show in both modes.
export function aboutSections(isPublic) {
  return [
    { key: "intro", text: DESCRIPTION },
    { key: "what", lead: ABOUT_WHAT.lead, text: ABOUT_WHAT.text },
    { key: "shows", heading: ABOUT_SHOWS.heading, items: ABOUT_SHOWS.items },
    ...(isPublic ? [{ key: "setup", heading: ABOUT_SETUP.heading, items: ABOUT_SETUP.items }] : []),
    { key: "scope", heading: ABOUT_SCOPE.heading, text: ABOUT_SCOPE.text },
    { key: "version", text: ABOUT_VERSION },
  ];
}
