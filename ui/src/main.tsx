import { FieldLabel, fieldGuides } from "./FieldHelp";
import { api } from "./api";
import { Review } from "./Review";
import type { State, Settings, Folder } from "./types";
import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const defaults: Record<string, string> = {
  company: "company",
  website: "website",
  person: "person",
  email: "email",
  company_website: "company_website",
  companies: "companies",
  attendees: "attendees",
};
const labels: Record<string, string> = {
  company: "Company name",
  website: "Company website",
  person: "Person name",
  email: "Person email",
  company_website: "Person’s company website",
  companies: "Other subject companies",
  attendees: "Meeting participants",
};
function App() {
  const [state, setState] = useState<State>({
    phase: "idle",
    server: "",
    progress: 0,
    total: 0,
    receipts: [],
  });
  const [vaults, setVaults] = useState<{ path: string; name: string }[]>([]);
  const [path, setPath] = useState("");
  const [inventory, setInventory] = useState<{
    path: string;
    name: string;
    folders: Folder[];
    count: number;
  }>();
  const [selected, setSelected] = useState<string[]>([]);
  const [profiles, setProfiles] = useState<Record<string, string>>({});
  const [namespace, setNamespace] = useState("");
  const [exclude, setExclude] = useState("Templates/*\nArchive/*");
  const [fields, setFields] = useState(defaults);
  const [identity, setIdentity] = useState("");
  const [scope, setScope] = useState("private");
  const [recipients, setRecipients] = useState("");
  const [limit, setLimit] = useState(50);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const busy =
    working ||
    [
      "connecting",
      "signing_in",
      "previewing",
      "reviewing",
      "importing",
    ].includes(state.phase);
  const initialized = useRef(false);
  useEffect(() => {
    let active = true;
    const refresh = () =>
      api("state")
        .then((s) => {
          if (active) {
            setState(s);
            if (!initialized.current) {
              initialized.current = true;
              const saved: Settings | undefined = s.settings;
              if (saved) {
                setPath(saved.source.vault);
                setNamespace(saved.source.namespace);
                setFields({ ...defaults, ...saved.source.fields });
                setIdentity(saved.source.identity_property || "");
                setExclude(saved.source.exclude.join("\n"));
                setScope(saved.scope);
                setRecipients(saved.people?.join(", ") || saved.group || "");
                setLimit(saved.max_records);
                setProfiles(
                  Object.fromEntries(
                    saved.source.folder_rules.map((r) => [r.folder, r.profile]),
                  ),
                );
                setSelected([
                  ...new Set(
                    saved.source.include.map((p) =>
                      p === "*.md" || p === "*.markdown"
                        ? "."
                        : p.replace(/\/\*\.(md|markdown)$/, ""),
                    ),
                  ),
                ]);
                api("inventory", { path: saved.source.vault })
                  .then(setInventory)
                  .catch((e) => setError(e.message));
              }
            }
          }
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    refresh();
    api("vaults")
      .then(setVaults)
      .catch((e) => setError(e.message));
    const timer = setInterval(refresh, 800);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  function changed() {
    setDirty(true);
    setConfirm(false);
  }
  async function action(path: string, body: unknown = {}) {
    setError("");
    setWorking(true);
    try {
      await api(path, body);
      setState(await api("state"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function choose() {
    setError("");
    setWorking(true);
    try {
      const result = await api("inventory", { path });
      setInventory(result);
      setSelected([]);
      setProfiles({});
      setNamespace(
        result.name
          .toLowerCase()
          .replace(/[^a-z0-9_-]+/g, "-")
          .slice(0, 70),
      );
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setWorking(false);
    }
  }
  async function preview() {
    const include = selected.flatMap((f) =>
      f === "." ? ["*.md", "*.markdown"] : [f + "/*.md", f + "/*.markdown"],
    );
    // Root-only selection excludes subfolders unless they are explicitly selected too.
    const omitted = inventory!.folders
      .filter(
        (f) =>
          f.path !== "." &&
          !selected.some(
            (s) => s !== "." && (f.path === s || f.path.startsWith(s + "/")),
          ),
      )
      .map((f) => f.path + "/*");
    const source = {
      type: "obsidian",
      vault: inventory!.path,
      vault_name: inventory!.name,
      namespace,
      include,
      exclude: [
        ...exclude
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        ...(selected.includes(".") ? omitted : []),
      ],
      fields,
      ...(identity ? { identity_property: identity } : {}),
      folder_rules: Object.entries(profiles)
        .filter(([folder]) => selected.includes(folder) && folder !== ".")
        .map(([folder, profile]) => ({ folder, profile })),
    };
    setDirty(false);
    setConfirm(false);
    await action("preview", {
      source,
      scope,
      max_records: limit,
      ...(scope === "people"
        ? {
            people: recipients
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          }
        : scope === "group"
          ? { group: recipients.trim() }
          : {}),
    });
  }
  const results = state.preview || [];
  return (
    <>
      <header>
        <a className="brand" href="#">
          b<span>brain</span>
          <small>IMPORT STUDIO</small>
        </a>
        <span className="local">
          <i /> Running on your computer
        </span>
      </header>
      <main>
        <section className="intro">
          <p className="eyebrow">YOUR KNOWLEDGE, CONNECTED</p>
          <h1>Bring your notes into Brain.</h1>
          <p>
            Choose what to bring, see where it belongs, then import with
            confidence.
          </p>
        </section>
        <div className="layout">
          <aside>
            <div className="step active">
              <b>1</b>
              <span>
                Choose your notes<small>Vault, folders and properties</small>
              </span>
            </div>
            <div className={"step " + (results.length ? "active" : "")}>
              <b>2</b>
              <span>
                Check the matches<small>A dry run, without importing</small>
              </span>
            </div>
            <div
              className={"step " + (state.phase === "complete" ? "active" : "")}
            >
              <b>3</b>
              <span>
                Import your snapshot<small>You decide when to save</small>
              </span>
            </div>
            <div className="aside-note">
              Original notes stay intact.
              <br />
              Private by default.
              <br />
              No notes through your assistant.
            </div>
          </aside>
          <div className="workspace">
            {(error || state.error) && (
              <div role="alert" className="alert">
                {error || state.error}
              </div>
            )}
            <section className="panel">
              <div className="section-title">
                <div>
                  <span className="eyebrow">CONNECTION</span>
                  <h2>Your destination</h2>
                </div>
                {state.account && (
                  <span className="pill success">Connected</span>
                )}
              </div>
              {state.account ? (
                <p>
                  <strong>{state.account.firm_name}</strong>
                  <span className="muted"> · {state.account.name}</span>
                </p>
              ) : (
                <p>
                  Connect with the Brain CLI account on this computer. Check the
                  workspace before continuing.
                </p>
              )}
              <p className="endpoint">{state.server}</p>
              <div className="actions">
                <button disabled={busy} onClick={() => action("connect")}>
                  {state.account ? "Check connection" : "Connect to Brain"}
                </button>
                <button
                  className="subtle"
                  disabled={busy}
                  onClick={() => action("login")}
                >
                  Sign in through browser
                </button>
              </div>
              {state.phase === "signing_in" && (
                <p role="status">
                  Complete sign-in in the browser window. No Keychain permission
                  is requested automatically.
                </p>
              )}
            </section>
            <section className="panel">
              <div className="section-title">
                <div>
                  <span className="eyebrow">01 / SELECTION</span>
                  <h2>Your Obsidian vault</h2>
                </div>
                <span className="pill">Markdown</span>
              </div>
              <fieldset disabled={busy}>
                <label>
                  Registered vault
                  <select
                    aria-label="Registered vault"
                    value={vaults.some((v) => v.path === path) ? path : ""}
                    onChange={(e) => {
                      setPath(e.target.value);
                      setInventory(undefined);
                      changed();
                    }}
                  >
                    <option value="">
                      Choose a vault or enter its path below
                    </option>
                    {vaults.map((v) => (
                      <option key={v.path} value={v.path}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="row">
                  <label className="grow">
                    Vault folder
                    <input
                      placeholder="/path/to/your/Obsidian vault"
                      value={path}
                      onChange={(e) => {
                        setPath(e.target.value);
                        setInventory(undefined);
                        changed();
                      }}
                    />
                  </label>
                  <button disabled={!path} onClick={choose}>
                    Load folders
                  </button>
                </div>
                {inventory && (
                  <>
                    <div className="folder-heading">
                      <strong>Choose folders</strong>
                      <span>{inventory.count} Markdown files found</span>
                    </div>
                    <p className="hint">
                      Folder selection includes subfolders. Templates and
                      Archive are excluded below.
                    </p>
                    <div className="folders">
                      {inventory.folders.map((f) => (
                        <div className="folder" key={f.path}>
                          <label className="check">
                            <input
                              type="checkbox"
                              checked={selected.includes(f.path)}
                              onChange={(e) => {
                                setSelected(
                                  e.target.checked
                                    ? [...selected, f.path]
                                    : selected.filter((s) => s !== f.path),
                                );
                                changed();
                              }}
                            />
                            <span>
                              {f.path === "." ? "Notes at vault root" : f.path}
                              <small>{f.count} files directly in folder</small>
                            </span>
                          </label>
                          {f.path !== "." && (
                            <select
                              aria-label={"Note type for " + f.path}
                              disabled={!selected.includes(f.path)}
                              value={profiles[f.path] || "notes"}
                              onChange={(e) => {
                                setProfiles({
                                  ...profiles,
                                  [f.path]: e.target.value,
                                });
                                changed();
                              }}
                            >
                              <option value="notes">General notes</option>
                              <option value="organization">
                                Company notes
                              </option>
                              <option value="person">Person notes</option>
                            </select>
                          )}
                        </div>
                      ))}
                    </div>
                    <p className="hint">
                      Company/person folders use the heading as a name hint when
                      structured fields are absent. They associate documents
                      with existing records; they never create companies or
                      people.
                    </p>
                    <details>
                      <summary>Selection and stable identity</summary>
                      <div className="two">
                        <div className="field">
                          <FieldLabel id="collection-id" title="Collection ID">
                            A unique label for this vault’s imports, such as
                            northwind-notes. Brain combines it with each note’s
                            file path (or stable ID) to recognise the same note
                            on later imports. Keep it unchanged to update
                            existing notes; changing it can create duplicates.
                            Use a different label for another vault.
                          </FieldLabel>
                          <input
                            id="collection-id"
                            value={namespace}
                            onChange={(e) => {
                              setNamespace(e.target.value);
                              changed();
                            }}
                          />
                          <small>
                            Identifies this vault’s imports so repeat runs
                            update the same notes.
                          </small>
                        </div>
                        <div className="field">
                          <FieldLabel id="maximum-notes" title="Maximum notes">
                            A safety limit on the number of non-empty Markdown
                            notes selected for one run. It counts files, not
                            companies, people or links. If your selection
                            exceeds this limit, the dry run stops: it does not
                            silently take the first few notes. Choose fewer
                            folders or increase the limit (up to 5,000).
                          </FieldLabel>
                          <input
                            id="maximum-notes"
                            type="number"
                            min="1"
                            max="5000"
                            value={limit}
                            onChange={(e) => {
                              setLimit(Number(e.target.value));
                              changed();
                            }}
                          />
                          <small>
                            Stops the run if the selection is larger; never
                            silently skips the rest.
                          </small>
                        </div>
                        <div className="field">
                          <FieldLabel
                            id="exclude-patterns"
                            title="Exclude patterns (one per line)"
                          >
                            Skip files whose path inside the vault matches a
                            pattern. For example, Archive/* skips notes under
                            Archive, including its subfolders. * means any
                            characters. Enter one pattern per line. These files
                            will not be previewed or imported.
                          </FieldLabel>
                          <textarea
                            id="exclude-patterns"
                            value={exclude}
                            onChange={(e) => {
                              setExclude(e.target.value);
                              changed();
                            }}
                          />
                        </div>
                        <div className="field">
                          <FieldLabel
                            id="stable-id"
                            title="Stable ID property (optional)"
                          >
                            Usually leave this blank: the note’s path identifies
                            it. Enable it before your first import if you plan
                            to rename or move notes. Enter an Obsidian property
                            name here, such as brain_id, and add a unique text
                            value to that property on every selected note. Keep
                            each value unchanged when moving or renaming the
                            note. You can add it in Obsidian’s Properties panel
                            or in the YAML block at the very top of the Markdown
                            file:
                            <pre>
                              {
                                "---\nbrain_id: acme-meeting-001\n---\n# Meeting with Acme"
                              }
                            </pre>
                            Missing or repeated values stop the run. Enabling
                            this after importing changes note identities and can
                            create duplicates.
                          </FieldLabel>
                          <input
                            id="stable-id"
                            placeholder="brain_id"
                            value={identity}
                            onChange={(e) => {
                              setIdentity(e.target.value);
                              changed();
                            }}
                          />
                          <small>
                            Optional protection against duplicate notes after a
                            rename or move.
                          </small>
                        </div>
                      </div>
                    </details>
                  </>
                )}
              </fieldset>
            </section>
            <section className="panel">
              <div className="section-title">
                <div>
                  <span className="eyebrow">02 / CONTEXT</span>
                  <h2>Properties and sharing</h2>
                </div>
              </div>
              <fieldset disabled={busy}>
                <p>
                  Tell the importer what your Obsidian properties are called.
                  These are the fields at the top of a note in Obsidian’s
                  Properties panel, saved between --- lines in Markdown. These
                  boxes contain property names, not company names, websites or
                  email addresses.
                </p>
                <div className="mapping-example">
                  <strong>Example: a company note in Obsidian</strong>
                  <pre>
                    {
                      "---\ncompany: Acme AI\nwebsite: https://acme.ai\n---\n# Meeting with Acme AI"
                    }
                  </pre>
                  <p>
                    With this note, set <strong>Company name</strong> to{" "}
                    <code>company</code> and <strong>Company website</strong> to{" "}
                    <code>website</code>. If your note uses{" "}
                    <code>URL: https://acme.ai</code>, enter <code>URL</code>{" "}
                    instead. Property names must match exactly, including
                    capitals.
                  </p>
                  <p>
                    Leave mappings blank if unused. Missing properties are
                    ignored. These settings read your notes; they do not add or
                    rename properties in Obsidian. Without properties, a
                    company/person folder can use the heading as a name to
                    review.
                  </p>
                </div>
                <h3>Which Obsidian property contains each value?</h3>
                <div className="two">
                  {Object.entries(fields).map(([k, v]) => (
                    <div className="field" key={k}>
                      <FieldLabel id={"mapping-" + k} title={labels[k]}>
                        {fieldGuides[k].help}
                      </FieldLabel>
                      <input
                        id={"mapping-" + k}
                        placeholder="Property name, or leave blank"
                        value={v}
                        onChange={(e) => {
                          setFields({ ...fields, [k]: e.target.value });
                          changed();
                        }}
                      />
                      <small>
                        {v ? (
                          <>
                            Example in your note:{" "}
                            <code>
                              {v}: {fieldGuides[k].example}
                            </code>
                          </>
                        ) : (
                          "Not used in this import."
                        )}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="sharing">
                  <div className="field">
                    <FieldLabel
                      id="sharing-scope"
                      title="Who can read these notes?"
                    >
                      Choose who can read the imported notes in Brain. Only me
                      keeps them private. Everyone means members of this Brain
                      workspace, not the public internet. Specific people and
                      groups must already exist in Brain. This applies to all
                      selected notes, and does not copy Obsidian permissions or
                      change existing notes’ sharing.
                    </FieldLabel>
                    <select
                      id="sharing-scope"
                      value={scope}
                      onChange={(e) => {
                        setScope(e.target.value);
                        setRecipients("");
                        changed();
                      }}
                    >
                      <option value="private">Only me</option>
                      <option value="firm">
                        Everyone in this Brain workspace
                      </option>
                      <option value="people">Specific people</option>
                      <option value="group">An existing group</option>
                    </select>
                  </div>
                  {["people", "group"].includes(scope) && (
                    <label>
                      {scope === "people"
                        ? "Member emails or names, separated by commas"
                        : "Group name"}
                      <input
                        value={recipients}
                        onChange={(e) => {
                          setRecipients(e.target.value);
                          changed();
                        }}
                      />
                    </label>
                  )}
                  <p className="hint">
                    Existing notes keep their audience. A conflicting setting
                    stops the import; changing this control does not reshare
                    them.
                  </p>
                </div>
                <div className="preview-callout">
                  <div>
                    <strong>Check before you commit.</strong>
                    <p>
                      Dry run sends the selected snapshot to Brain for matching.
                      It saves no sources, links or reviews.
                    </p>
                  </div>
                  <button
                    className="primary"
                    disabled={
                      !state.account ||
                      !inventory ||
                      !selected.length ||
                      !namespace ||
                      !limit
                    }
                    onClick={preview}
                  >
                    Run dry run <span aria-hidden="true">→</span>
                  </button>
                </div>
              </fieldset>
            </section>
            {busy && (
              <div className="panel progress" role="status">
                <strong>
                  {state.phase === "importing"
                    ? state.message
                    : state.phase === "reviewing"
                      ? "Saving your choice…"
                      : state.phase === "previewing"
                        ? "Checking your notes against Brain…"
                        : "Connecting to Brain…"}
                </strong>
                {state.total > 0 && (
                  <>
                    <progress max={state.total} value={state.progress} />
                    <span>
                      {state.progress} of {state.total}
                    </span>
                  </>
                )}
              </div>
            )}
            {!!results.length && (
              <Review
                state={state}
                dirty={dirty}
                busy={busy}
                confirm={confirm}
                setConfirm={setConfirm}
                onChoose={(record, choice) => {
                  setConfirm(false);
                  void action("review", {
                    record,
                    sha256: state.plan!.sha256,
                    ...choice,
                  });
                }}
                onImport={() =>
                  action("import", { sha256: state.plan!.sha256 })
                }
              />
            )}
            {state.phase === "error" && state.receipts.length > 0 && (
              <section className="panel">
                <h2>Import stopped after {state.receipts.length} receipts</h2>
                <p>
                  Earlier successful writes remain in Brain. Inspect them before
                  running a fresh dry run. Stable source IDs allow safe repeats.
                </p>
                <p>{state.receipt_path}</p>
              </section>
            )}
            <footer>
              Obsidian first. Notion and custom sources remain available through
              the importer CLI.
            </footer>
          </div>
        </div>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
