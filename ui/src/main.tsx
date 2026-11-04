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
                        <label>
                          Collection ID
                          <input
                            value={namespace}
                            onChange={(e) => {
                              setNamespace(e.target.value);
                              changed();
                            }}
                          />
                          <small>Keep this unchanged on repeat imports.</small>
                        </label>
                        <label>
                          Maximum notes
                          <input
                            type="number"
                            min="1"
                            max="5000"
                            value={limit}
                            onChange={(e) => {
                              setLimit(Number(e.target.value));
                              changed();
                            }}
                          />
                        </label>
                        <label>
                          Exclude patterns (one per line)
                          <textarea
                            value={exclude}
                            onChange={(e) => {
                              setExclude(e.target.value);
                              changed();
                            }}
                          />
                        </label>
                        <label>
                          Stable ID property (optional)
                          <input
                            placeholder="brain_id"
                            value={identity}
                            onChange={(e) => {
                              setIdentity(e.target.value);
                              changed();
                            }}
                          />
                          <small>
                            Set before the first import. Required on every
                            selected note if enabled.
                          </small>
                        </label>
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
                  Map your Obsidian properties to the identity clues Brain
                  should check.
                </p>
                <div className="two">
                  {Object.entries(fields).map(([k, v]) => (
                    <label key={k}>
                      {labels[k]}
                      <input
                        value={v}
                        onChange={(e) => {
                          setFields({ ...fields, [k]: e.target.value });
                          changed();
                        }}
                      />
                    </label>
                  ))}
                </div>
                <div className="sharing">
                  <label>
                    Who can read these notes?
                    <select
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
                  </label>
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
