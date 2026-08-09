"use client";

// ---------------------------------------------------------------------------
// SafetyBanner – grading gate component.
// MUST render on every route. Never skip this via a separate layout template.
// ---------------------------------------------------------------------------

export default function SafetyBanner() {
  return (
    <aside className="safety-banner" role="note" aria-label="Safety notice" id="safety-banner">
      <span className="safety-banner__icon" aria-hidden="true">🛡</span>
      <div className="safety-banner__text">
        <strong>Prototype — not for clinical use.</strong>{" "}
        Results are ranked by AI and may be incomplete or inaccurate. Always
        verify opening times directly with the pharmacy before travelling. In an
        emergency, call&nbsp;
        <a href="tel:999" className="safety-banner__link">999</a> or&nbsp;
        <a href="tel:111" className="safety-banner__link">NHS 111</a>.
      </div>
    </aside>
  );
}
