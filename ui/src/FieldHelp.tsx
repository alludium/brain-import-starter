import { useId, type ReactNode } from "react";

export function FieldHelp({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="field-help">
      <button
        type="button"
        className="info-button"
        popoverTarget={id}
        aria-label={`About ${title}`}
      >
        ⓘ
      </button>
      <div id={id} popover="auto" className="help-popover">
        <strong>{title}</strong>
        <div className="help-body">{children}</div>
        <button type="button" popoverTarget={id} popoverTargetAction="hide">
          Close explanation
        </button>
      </div>
    </div>
  );
}
export function FieldLabel({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="field-caption">
      <label htmlFor={id}>{title}</label>
      <FieldHelp title={title}>{children}</FieldHelp>
    </div>
  );
}
export const fieldGuides: Record<string, { example: string; help: string }> = {
  company: {
    example: "Acme AI",
    help: "The property containing the company’s name. Enter the property name here (for example Company), not Acme AI. The importer reads its value from each note. A name by itself requires your confirmation.",
  },
  website: {
    example: "https://acme.ai",
    help: "The property containing the company’s website on company or meeting notes. Enter website, URL, or whatever your vault calls it. Brain compares the domain with known companies. This mapping is used when no main person is extracted from the note.",
  },
  person: {
    example: "Maya Lindqvist",
    help: "The property naming the main person a note is about. Enter its property name, for example person or Contact. For a list of meeting attendees, use Meeting participants instead.",
  },
  email: {
    example: "maya@acme.ai",
    help: "The property containing the main person’s email address. Enter the property name here, not an email address. An exact known email can corroborate the person’s identity. It does not supply email addresses for a list of attendees.",
  },
  company_website: {
    example: "https://acme.ai",
    help: "The property containing the employer’s website on a note with a main person. If a person is extracted, this is used instead of Company website to identify their company. It is not an automatic fallback for meeting/company notes. If your vault uses website for both, enter website in both boxes.",
  },
  companies: {
    example: '["Acme AI", "Kestrel Data"]',
    help: "A property containing a list of companies this note is about. Each list entry is a name to review separately. It does not scan body text or add every competitor mentioned. Leave blank if you do not have this property.",
  },
  attendees: {
    example: '["Maya Lindqvist"]',
    help: "A property containing a list of meeting participants’ names, including Obsidian links such as [[People/Maya Lindqvist]]. These are name-only hints; each needs confirmation even when Brain finds just one candidate. Leave blank if unused.",
  },
};
