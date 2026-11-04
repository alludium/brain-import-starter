const fragment = new URLSearchParams(location.hash.slice(1));
const key = fragment.get("key") || sessionStorage.getItem("import-key") || "";
if (fragment.has("key")) {
  sessionStorage.setItem("import-key", key);
  history.replaceState(null, "", location.pathname);
}
export async function api(path: string, body?: unknown) {
  const response = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "X-Import-Key": key,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}
