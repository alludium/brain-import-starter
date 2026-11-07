import { CandidateFacts } from "./MatchExplanation";
import { useState } from "react";
import { api } from "./api";
import type { Candidate, Match } from "./types";

export type Choice = {
  fingerprint: string;
  action: string;
  entity_id?: string;
};
export function MatchChoice({
  match,
  record,
  sha,
  disabled,
  onChoose,
}: {
  match: Match;
  record: number;
  sha: string;
  disabled: boolean;
  onChoose: (record: number, choice: Choice) => void;
}) {
  const [query, setQuery] = useState("");
  const [found, setFound] = useState<Candidate[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const choose = (action: string, entity_id?: string) =>
    onChoose(record, { fingerprint: match.fingerprint!, action, entity_id });
  if (!match.fingerprint)
    return <p className="hint">Update Brain to resolve this match here.</p>;
  if (match.reviewed)
    return (
      <div className="choice-saved">
        <strong>
          {match.status === "approved"
            ? "Confirmed by you"
            : match.status === "rejected"
              ? "Leave unlinked"
              : "Review later in Sources"}
        </strong>
        {match.entity_id && (
          <p>{match.candidates.find((c) => c.id === match.entity_id)?.name}</p>
        )}
        <button disabled={disabled} onClick={() => choose("reset")}>
          Change choice
        </button>
      </div>
    );
  if (!["pending", "deferred", "unmatched"].includes(match.status)) return null;
  async function search() {
    setSearching(true);
    setError("");
    setFound(null);
    try {
      const response = await api("search", { record, sha256: sha, query });
      setFound(
        response.candidates.filter(
          (c: Candidate) => c.type === match.evidence.type,
        ),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSearching(false);
    }
  }
  return (
    <fieldset className="match-choice" disabled={disabled || searching}>
      <legend>
        Resolve this {match.evidence.type === "person" ? "person" : "company"}
      </legend>
      <div className="candidate-choices">
        {match.candidates.map((c) => (
          <button key={c.id} onClick={() => choose("approve", c.id)}>
            Choose {c.name}
          </button>
        ))}
      </div>
      <div className="match-search">
        <label>
          Search another{" "}
          {match.evidence.type === "person" ? "person" : "company"}
          <input
            value={query}
            maxLength={200}
            placeholder="Name in Brain…"
            onChange={(e) => {
              setQuery(e.target.value);
              setFound(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && query.trim()) {
                e.preventDefault();
                void search();
              }
            }}
          />
        </label>
        <button disabled={!query.trim()} onClick={() => void search()}>
          {searching ? "Searching…" : "Search Brain"}
        </button>
      </div>
      <p className="hint">
        Existing identities visible to this note’s audience. No new company or
        person is created.
      </p>
      {error && <p role="alert">{error}</p>}
      {found && (
        <div className="candidate-choices" aria-live="polite">
          {found.length ? (
            found.map((c) => (
              <div className="search-candidate" key={c.id}>
                <button onClick={() => choose("approve", c.id)}>
                  Choose {c.name}
                </button>
                <CandidateFacts candidate={c} />
              </div>
            ))
          ) : (
            <p>No identities of this type found. Try a different name.</p>
          )}
        </div>
      )}
      <div className="choice-actions">
        <button onClick={() => choose("reject")}>Leave unlinked</button>
        <button onClick={() => choose("defer")}>Review later</button>
      </div>
    </fieldset>
  );
}
