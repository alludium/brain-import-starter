import { useState } from "react";
import type { State, Preview } from "./types";
function category(p: Preview) {
  return p.items.some((m) => m.status === "pending" || m.status === "deferred")
    ? "review"
    : p.items.some((m) => m.status === "automatic" || m.status === "approved")
      ? "matched"
      : "unmatched";
}
export function Review({
  state,
  dirty,
  busy,
  confirm,
  setConfirm,
  onImport,
}: {
  state: State;
  dirty: boolean;
  busy: boolean;
  confirm: boolean;
  setConfirm: (value: boolean) => void;
  onImport: () => void;
}) {
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const results = state.preview || [];
  const counts = {
    matched: results.filter((p) => category(p) === "matched").length,
    review: results.filter((p) => category(p) === "review").length,
    unmatched: results.filter((p) => category(p) === "unmatched").length,
  };
  const filtered = results.filter(
    (p) =>
      (tab === "all" || category(p) === tab) &&
      p.title.toLowerCase().includes(query.toLowerCase()),
  );
  const viewer = state.viewer_url || state.server.replace(/\/mcp\/?$/, "");
  return (
    <section className="panel results" aria-label="Dry run results">
      <div className="section-title">
        <div>
          <span className="eyebrow">03 / REVIEW</span>
          <h2>Your dry run</h2>
        </div>
        <span className="pill success">{results.length} notes checked</span>
      </div>
      <p>
        {state.phase === "complete"
          ? "This is the snapshot you imported."
          : "Nothing has been imported by this dry run."}{" "}
        Matches reflect the current knowledge visible to your chosen audience.
      </p>
      {dirty && (
        <div className="alert">
          Settings changed. Run a new dry run before importing.
        </div>
      )}
      {state.message && <p role="status">{state.message}</p>}
      <div className="metrics">
        <div>
          <strong>{counts.matched}</strong>
          <span>Matched notes</span>
        </div>
        <div>
          <strong>{counts.review}</strong>
          <span>Need review</span>
        </div>
        <div>
          <strong>{counts.unmatched}</strong>
          <span>No active match</span>
        </div>
      </div>
      <div className="result-tools">
        <div className="tabs" aria-label="Filter notes">
          {["all", "matched", "review", "unmatched"].map((t) => (
            <button key={t} aria-pressed={tab === t} onClick={() => setTab(t)}>
              {
                (
                  {
                    all: "All notes",
                    matched: "Matched",
                    review: "Needs review",
                    unmatched: "No active match",
                  } as Record<string, string>
                )[t]
              }
            </button>
          ))}
        </div>
        <input
          aria-label="Search preview notes"
          placeholder="Find a note…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="notes">
        {filtered.map((p) => (
          <details className="note" key={p.external_id}>
            <summary>
              <span>
                <strong>{p.title}</strong>
                <small>
                  {p.disposition === "unchanged"
                    ? "Already imported · decisions retained"
                    : p.disposition === "revision"
                      ? "New version"
                      : "New note"}{" "}
                  · {p.scope === "private" ? "Only me" : p.scope}
                </small>
              </span>
              <span className={"pill " + category(p)}>
                {category(p) === "review"
                  ? "Needs review"
                  : category(p) === "matched"
                    ? "Matched"
                    : "No active match"}
              </span>
            </summary>
            <div className="matches">
              {!p.items.length && (
                <p>
                  No supported identity clues matched. The note will remain
                  unlinked.
                </p>
              )}
              {p.items.map((m, i) => (
                <article key={i}>
                  <div>
                    <strong>
                      {m.evidence.name ||
                        m.evidence.domain ||
                        m.evidence.email ||
                        "Heading"}
                    </strong>
                    <span className="pill">
                      {(
                        {
                          automatic: "Automatic match",
                          pending: "Human review",
                          unmatched: "No match",
                          approved: "Confirmed",
                          rejected: "Rejected",
                          deferred: "Deferred",
                        } as Record<string, string>
                      )[m.status] || m.status}
                    </span>
                  </div>
                  <p>{m.reason}</p>
                  <p className="hint">
                    Evidence:{" "}
                    {[
                      m.evidence.location,
                      m.evidence.domain,
                      m.evidence.email,
                      m.evidence.role,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {!!m.candidates.length && (
                    <ul>
                      {m.candidates.map((c) => (
                        <li key={c.id}>
                          {c.name}{" "}
                          <span className="muted">
                            · {c.type === "organization" ? "Company" : "Person"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          </details>
        ))}
        {!filtered.length && <p>No notes match this filter.</p>}
      </div>
      {state.phase !== "complete" && (
        <div className="confirm">
          <p>
            Uncertain notes will be imported with pending matches in{" "}
            <strong>Sources → Needs review</strong>. Unmatched notes stay
            unlinked. This imports every note in the snapshot, including those
            hidden by the filter.
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={confirm}
              disabled={busy || dirty || state.phase !== "ready"}
              onChange={(e) => setConfirm(e.target.checked)}
            />
            <span>
              I have reviewed these {results.length} notes and their sharing
              settings.
            </span>
          </label>
          <button
            className="primary"
            disabled={busy || dirty || !confirm || state.phase !== "ready"}
            onClick={() => {
              setConfirm(false);
              onImport();
            }}
          >
            Import {results.length} notes
          </button>
          <p className="hint">
            We recheck the matches before writing. If they changed, you’ll
            review them again.
          </p>
        </div>
      )}
      {state.phase === "complete" && (
        <div className="completion" role="status">
          <h3>{state.receipts.length} notes processed</h3>
          <p>
            {state.receipts.filter((r) => r.created).length} created or
            versioned · {state.receipts.filter((r) => !r.created).length}{" "}
            unchanged
          </p>
          <a
            className="button"
            href={viewer + "/sources?view=review"}
            target="_blank"
            rel="noreferrer"
          >
            Open Sources review ↗
          </a>
        </div>
      )}
      <details className="saved">
        <summary>Saved locally on this computer</summary>
        <p>Plan: {state.plan_path}</p>
        {state.receipt_path && <p>Receipts: {state.receipt_path}</p>}
        <p className="hint">
          Plans contain original note text. Keep these files private. Closing
          this window does not cancel a running import.
        </p>
      </details>
    </section>
  );
}
