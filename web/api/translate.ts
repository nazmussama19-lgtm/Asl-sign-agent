// POST /api/translate  { text, to: "en" | "fr" }  -> { text }
// Short sentences for Text to Sign, translated by the same free AI providers.
import { AUTO_ORDER, complete, isAvailable } from "./_lib/llm.js";

interface Req { method?: string; body?: unknown }
interface Res { status(code: number): Res; json(body: unknown): void; setHeader(name: string, value: string): void }

export default async function handler(req: Req, res: Res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") { res.status(405).json({ error: "Use POST" }); return; }
  const body = (typeof req.body === "string" ? JSON.parse(req.body) : req.body) as { text?: string; to?: string };
  const text = String(body?.text ?? "").slice(0, 300).trim();
  const to = body?.to === "fr" ? "French" : "English";
  if (!text) { res.status(400).json({ error: "Empty text" }); return; }
  const messages = [
    { role: "system" as const, content: `Translate the user's text to ${to}. Reply with the translation only, no quotes, no comments.` },
    { role: "user" as const, content: text },
  ];
  for (const p of AUTO_ORDER.filter(isAvailable)) {
    try {
      const out = await complete(p, messages);
      if (out) { res.status(200).json({ text: out }); return; }
    } catch { /* next provider */ }
  }
  res.status(503).json({ error: "Translation is unavailable" });
}
