// "What we're delivering" (20 Oct): the deal brief as its own card, shared by the live deal page and the locked record.
// Every word is the owner-confirmed brief; nothing here is generated.
import { confirmedBy } from "./dealpage.js";
import { Icon } from "./Drawer.jsx";

const INFO = "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z";

export default function BriefCard({ brief }) {
  if (!brief) return null;
  const by = confirmedBy(brief);
  return (
    <section className="dp-card dp-brief-card">
      <div className="dp-sec-head">
        <div>
          <span className="dp-eyebrow">Deal brief</span>
          <h2>What we're delivering</h2>
        </div>
      </div>
      <div className="dp-brief-body">
        <p className="dp-brief">{brief.summary}</p>
        {brief.deliverables?.length > 0 && (
          <ul className="dp-deliverables">
            {brief.deliverables.map((d) => <li key={d}>{d}</li>)}
          </ul>
        )}
        <footer className="dp-confirmed">
          <span className="dp-avatar-sm" aria-hidden="true">{by.initials}</span>
          <span>
            Confirmed by <strong>{by.name}</strong>{by.role ? `, ${by.role}` : ""}{by.basis ? ` · from ${by.basis}` : ""}
          </span>
        </footer>
        {brief.needs_reconfirmation && (
          <div className="dp-notice" role="status"><Icon d={INFO} size={16} /><p>{brief.reconfirm_note}</p></div>
        )}
      </div>
    </section>
  );
}
