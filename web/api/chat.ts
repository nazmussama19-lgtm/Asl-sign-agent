// POST /api/chat  { text, lang, history, provider, compare }  -> { replies: Reply[] }
// GET  /api/chat  -> { providers: [{ id, label, model }] }   (only the configured ones)
import { AUTO_ORDER, LABELS, SYSTEM, complete, isAvailable, modelFor, shortError, type Message, type Provider } from "./_lib/llm.js";

interface Req { method?: string; body?: unknown; headers: Record<string, string | string[] | undefined> }
interface Res { status(code: number): Res; json(body: unknown): void; setHeader(name: string, value: string): void }

interface Body { text?: string; lang?: "en" | "fr"; history?: [string, string][]; provider?: string; compare?: boolean }
export interface Reply { text: string; provider: Provider; model: string; seconds: number; note?: string }

// Best-effort per-instance limit so one visitor cannot drain the free quotas.
const hits = new Map<string, { n: number; t: number }>();
function allowed(ip: string): boolean {
  const now = Date.now();
  const h = hits.get(ip);
  if (!h || now - h.t > 60 * 60 * 1000) { hits.set(ip, { n: 1, t: now }); return true; }
  h.n += 1;
  return h.n <= 60;
}

export default async function handler(req: Req, res: Res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method === "GET") {
    res.status(200).json({ providers: AUTO_ORDER.filter(isAvailable).map((id) => ({ id, label: LABELS[id], model: modelFor(id) })) });
    return;
  }
  if (req.method !== "POST") { res.status(405).json({ error: "Use POST" }); return; }

  const ip = String(req.headers["x-forwarded-for"] ?? "").split(",")[0].trim() || "unknown";
  if (!allowed(ip)) { res.status(429).json({ error: "Too many messages this hour" }); return; }

  const body = (typeof req.body === "string" ? JSON.parse(req.body) : req.body) as Body;
  const text = String(body?.text ?? "").slice(0, 300).trim();
  if (!text) { res.status(400).json({ error: "Empty message" }); return; }
  const lang = body.lang === "fr" ? "fr" : "en";
  const history = (Array.isArray(body.history) ? body.history : []).slice(-4);
  const messages: Message[] = [{ role: "system", content: SYSTEM[lang] }];
  for (const [u, a] of history) {
    messages.push({ role: "user", content: String(u).slice(0, 300) }, { role: "assistant", content: String(a).slice(0, 600) });
  }
  messages.push({ role: "user", content: text });

  const ask = async (p: Provider): Promise<Reply> => {
    const t0 = Date.now();
    const out = await complete(p, messages);
    if (!out) throw new Error("empty reply");
    return { text: out, provider: p, model: modelFor(p), seconds: (Date.now() - t0) / 1000 };
  };

  if (body.compare) {
    const chosen: Provider[] = (["groq", "gemini"] as Provider[]).filter(isAvailable);
    const replies = await Promise.all(chosen.map(async (p) => {
      const t0 = Date.now();
      try { return await ask(p); } catch (e) {
        return { text: "", provider: p, model: modelFor(p), seconds: (Date.now() - t0) / 1000, note: `No answer (${shortError(e)})` };
      }
    }));
    res.status(200).json({ replies });
    return;
  }

  // Chosen provider first, then the others; the browser falls back to local rules if all fail.
  const requested = AUTO_ORDER.includes(body.provider as Provider) ? (body.provider as Provider) : null;
  const chain = requested ? [requested, ...AUTO_ORDER.filter((p) => p !== requested)] : AUTO_ORDER;
  const skipped: Provider[] = [];
  for (const p of chain.filter(isAvailable)) {
    try {
      const reply = await ask(p);
      if (skipped.length) reply.note = `${skipped.map((s) => LABELS[s]).join(", ")} did not answer, so ${LABELS[p]} replied.`;
      res.status(200).json({ replies: [reply] });
      return;
    } catch {
      skipped.push(p);
    }
  }
  res.status(503).json({ error: "No AI provider answered", skipped });
}
