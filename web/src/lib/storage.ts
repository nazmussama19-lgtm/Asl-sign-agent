// localStorage with a safe fallback: private windows or blocked storage must never break the app.
const memory = new Map<string, string>();

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = globalThis.localStorage?.getItem(key) ?? memory.get(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown) {
  const raw = JSON.stringify(value);
  memory.set(key, raw);
  try {
    globalThis.localStorage?.setItem(key, raw);
  } catch {
    // quota or privacy mode: keep the in-memory copy
  }
}

export function remove(key: string) {
  memory.delete(key);
  try { globalThis.localStorage?.removeItem(key); } catch { /* ignore */ }
}
