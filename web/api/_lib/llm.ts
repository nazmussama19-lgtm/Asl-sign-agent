// Server side only (Vercel function): calls Groq and Gemini with keys that never reach the browser.
// Port of conversation.py; both providers expose an OpenAI-compatible endpoint.

export type Provider = "groq" | "groq_fast" | "gemini";
export const AUTO_ORDER: Provider[] = ["groq", "groq_fast", "gemini"];
export const LABELS: Record<Provider, string> = { groq: "Groq", groq_fast: "Groq (fast)", gemini: "Gemini" };

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions";
const TIMEOUT_MS = 12000;
const MAX_TOKENS = 300;

const env = (name: string, fallback = "") => (process.env[name] ?? "").trim() || fallback;

export function modelFor(p: Provider): string {
  if (p === "groq") return env("GROQ_MODEL", "openai/gpt-oss-120b");
  if (p === "groq_fast") return env("GROQ_FAST_MODEL", "openai/gpt-oss-20b");
  return env("GEMINI_MODEL", "gemini-3.8-flash");
}

export function isAvailable(p: Provider): boolean {
  return Boolean(p === "gemini" ? env("GEMINI_API_KEY") : env("GROQ_API_KEY"));
}

export const SYSTEM: Record<"en" | "fr", string> = {
  en:
    "You are Nova, the warm and clever assistant of a sign-language application. " +
    "The user's message comes from fingerspelling recognition: it may contain small errors, " +
    "missing words or telegraphic grammar. Silently infer the intended meaning, then answer " +
    "the actual question directly, naturally and helpfully, like a good friend would. " +
    "Interpretation examples (never mention them): 'HOW YOU DO' means 'how are you doing?'; " +
    "'WHAT TIME' means 'what time is it?'; 'U HUNGRY' means 'are you hungry?'. " +
    "Hard rules: never comment on spelling, grammar or sign language; never ask the user to " +
    "repeat, practice or sign anything; never describe gestures. Be engaging: answer, then " +
    "optionally ask ONE short natural follow-up question. Reply in English, 1 to 3 short sentences, " +
    "plain text without markdown.",
  fr:
    "Tu es Nova, l'assistant chaleureux et malin d'une application de langue des signes. " +
    "Le message de l'utilisateur provient d'une reconnaissance d'épellation : petites erreurs, " +
    "mots manquants ou style télégraphique possibles. Devine silencieusement le sens voulu, puis " +
    "réponds directement, naturellement et utilement à la vraie question, comme un bon ami. " +
    "Exemples d'interprétation (ne jamais les mentionner) : 'COMMENT TU VA' signifie " +
    "'comment vas-tu ?' ; 'QUELLE HEURE' signifie 'quelle heure est-il ?' ; 'TU FAIM' signifie " +
    "'as-tu faim ?'. Règles strictes : ne jamais commenter l'orthographe, la grammaire ou la " +
    "langue des signes ; ne jamais demander de répéter, de s'entraîner ou de signer ; ne jamais " +
    "décrire de gestes. Sois engageant : réponds, puis pose éventuellement UNE courte question " +
    "naturelle. Réponds en français, en 1 à 3 phrases courtes, en texte brut sans markdown.",
};

export interface Message { role: "system" | "user" | "assistant"; content: string }

async function post(url: string, key: string, payload: Record<string, unknown>) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!res.ok) {
    // Visible in the Vercel function logs; the provider's message says why (model name, quota...). Keys are never logged.
    const detail = (await res.text().catch(() => "")).slice(0, 300);
    console.error(`[llm] ${new URL(url).host} ${payload.model} -> HTTP ${res.status}: ${detail}`);
    throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status });
  }
  const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  return (data.choices?.[0]?.message?.content ?? "").trim();
}

/** One completion; tuning options a model refuses (HTTP 400) are dropped and the call retried once. */
export async function complete(p: Provider, messages: Message[], extraOverride?: Record<string, unknown>): Promise<string> {
  const url = p === "gemini" ? GEMINI_URL : GROQ_URL;
  const key = p === "gemini" ? env("GEMINI_API_KEY") : env("GROQ_API_KEY");
  // gpt-oss models reason before answering: keep it short and out of the reply
  const extra = extraOverride ?? (p === "gemini" ? { reasoning_effort: "low" } : { reasoning_effort: "low", include_reasoning: false });
  const base = { model: modelFor(p), messages, temperature: 0.7, max_tokens: MAX_TOKENS };
  try {
    return await post(url, key, { ...base, ...extra });
  } catch (e) {
    if ((e as { status?: number }).status === 400 && Object.keys(extra).length) return post(url, key, base);
    throw e;
  }
}

export function shortError(e: unknown): string {
  const status = (e as { status?: number }).status;
  if (status === 429) return "rate limit reached";
  if (status) return `HTTP ${status}`;
  if ((e as Error)?.name === "TimeoutError") return "timeout";
  return "unavailable";
}
