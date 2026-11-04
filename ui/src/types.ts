export type Folder = { path: string; count: number };
export type Candidate = { id: string; name: string; type: string };
export type Match = {
  fingerprint?: string;
  entity_id?: string;
  reviewed?: boolean;
  status: string;
  reason: string;
  evidence: {
    type?: string;
    name?: string;
    domain?: string;
    email?: string;
    location?: string;
    role?: string;
  };
  candidates: Candidate[];
};
export type Preview = {
  title: string;
  external_id: string;
  disposition: string;
  scope: string;
  items: Match[];
};
export type Settings = {
  scope: string;
  people?: string[];
  group?: string;
  max_records: number;
  source: {
    vault: string;
    namespace: string;
    include: string[];
    exclude: string[];
    fields: Record<string, string>;
    identity_property?: string;
    folder_rules: { folder: string; profile: string }[];
  };
};
export type State = {
  settings?: Settings;
  phase: string;
  server: string;
  viewer_url?: string;
  account?: { name: string; firm_name: string };
  error?: string;
  message?: string;
  progress: number;
  total: number;
  preview?: Preview[];
  plan?: { sha256: string; count: number };
  plan_path?: string;
  receipt_path?: string;
  receipts: { source_id: string; created: boolean }[];
};
