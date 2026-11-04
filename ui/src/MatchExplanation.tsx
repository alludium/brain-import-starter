import type { Candidate, Match } from "./types";

const names = (candidates: Candidate[]) =>
  candidates.map((c) => `“${c.name}”`).join(", ");
export function explanation(match: Match) {
  const { evidence: e, candidates: all } = match;
  if (
    match.reviewed ||
    ["approved", "rejected", "deferred"].includes(match.status)
  )
    return match.reason;
  const kind = e.type === "person" ? "person" : "company";
  const identifier = e.email || e.domain;
  const label = e.email ? "email" : "website";
  if (!identifier)
    return `Only a name was extracted for this ${kind}. ${all.length === 1 ? `Brain found one candidate, ${names(all)}, but a name alone does not prove it is the same ${kind}.` : all.length ? `Brain found ${all.length} possible records with this name.` : "Brain found no candidate for this name."} No ${e.type === "person" ? "email" : "company website"} was extracted for this subject using the current property mappings. Confirm only if you recognise the record, or adjust the mappings and run another dry run.`;
  // Matching basis comes from Brain's audience-filtered comparison, not guessed from display names.
  if (!all.every((c) => c.matched_on !== undefined)) return match.reason;
  const nameMatches = all.filter((c) => c.matched_on?.includes("name"));
  const idMatches = all.filter((c) => c.matched_on?.includes(label));
  if (
    e.name &&
    nameMatches.length &&
    idMatches.length &&
    !nameMatches.some((c) => idMatches.some((i) => i.id === c.id))
  )
    return `The extracted name “${e.name}” matches ${names(nameMatches)} in Brain, but the ${label} “${identifier}” matches ${names(idMatches)}. These point to different records. Check the note before choosing which one it is about.`;
  if (match.status === "automatic")
    return `The extracted ${label} “${identifier}” identifies one known ${kind}${e.name ? ` and the name “${e.name}” agrees` : ""}. Brain can link this automatically.`;
  if (!idMatches.length)
    return `The extracted ${label} “${identifier}” was not found on a ${kind} visible to this audience.${nameMatches.length ? ` The name “${e.name}” matches ${names(nameMatches)}, but the ${label} does not confirm that match.` : " The extracted name also has no confirmed match."} Check the note, search another record, or leave it unlinked.`;
  if (e.name && !nameMatches.length)
    return `The ${label} “${identifier}” matches ${names(idMatches)}, but the extracted name “${e.name}” does not match a known name for that record. Confirm only if you know they refer to the same ${kind}.`;
  return `The extracted clues do not identify just one ${kind}: ${label} “${identifier}” matches ${names(idMatches)}. Review the records below before choosing.`;
}
export function CandidateFacts({ candidate }: { candidate: Candidate }) {
  return (
    <span className="candidate-facts">
      {candidate.matched_on !== undefined && (
        <span>
          {candidate.matched_on.length
            ? `Matches extracted ${candidate.matched_on.join(" and ")}`
            : "Selected manually; does not match the extracted name or website/email"}
        </span>
      )}
      {!!candidate.websites?.length && (
        <span>Website in Brain: {candidate.websites.join(", ")}</span>
      )}
      {!!candidate.emails?.length && (
        <span>Email in Brain: {candidate.emails.join(", ")}</span>
      )}
    </span>
  );
}
export function MatchExplanation({
  match,
  viewer,
}: {
  match: Match;
  viewer: string;
}) {
  const e = match.evidence;
  const source = e.location?.startsWith("properties.")
    ? `Obsidian property “${e.location.slice(11)}”`
    : e.location?.startsWith("folder.")
      ? `Heading or filename, using the “${e.location.slice(7)}” folder’s note type`
      : "Note heading or filename";
  return (
    <div className="match-explanation">
      <p className="match-reason">{explanation(match)}</p>
      <div className="extracted-clues">
        <strong>Extracted from this note</strong>
        <dl>
          <dt>{e.type === "person" ? "Person name" : "Company name"}</dt>
          <dd>{e.name || "Not extracted"}</dd>
          <dt>{e.type === "person" ? "Email" : "Website"}</dt>
          <dd>{e.email || e.domain || "Not extracted for this subject"}</dd>
          <dt>{e.name ? "Name came from" : "Clue came from"}</dt>
          <dd>{source}</dd>
        </dl>
      </div>
      {!!match.candidates.length && (
        <div className="known-records">
          <strong>Compared with records in Brain</strong>
          <ul>
            {match.candidates.map((c) => (
              <li key={c.id}>
                <strong>{c.name}</strong>
                <CandidateFacts candidate={c} />
                <a
                  href={`${viewer}/${c.type === "person" ? "people" : "companies"}/${encodeURIComponent(c.id)}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open {c.name} in Brain ↗
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
