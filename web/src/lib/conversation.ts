// Browser side of the conversation: asks /api/chat (Groq, Gemini), and answers with the same local
// rules as the Python app when no AI is reachable, so the demo never goes silent.
import type { Vocabulary } from "./agent";

export type ProviderId = "auto" | "groq" | "groq_fast" | "gemini";
export interface ProviderInfo { id: Exclude<ProviderId, "auto">; label: string; model: string }
export interface Reply { text: string; provider: string; model: string; seconds: number; note?: string; lang: "en-US" | "fr-FR" }

export const MAX_CLOUD_REPLIES = 40;

export function detectLang(text: string, vocab: Vocabulary): "fr" | "en" {
  const words = text.toUpperCase().match(/[A-Za-z']+/g) ?? [];
  let fr = 0, en = 0;
  for (const w of words) {
    if (vocab.fr.has(w) && !vocab.en.has(w)) fr++;
    if (vocab.en.has(w) && !vocab.fr.has(w)) en++;
  }
  return fr >= en && fr > 0 ? "fr" : "en";
}

const RULES_FR: [string[], string][] = [
  [["BONJOUR", "SALUT", "COUCOU", "HELLO"], "Bonjour ! Comment vas-tu ?"],
  [["CA VA", "COMMENT VAS", "COMMENT ALLEZ"], "Je vais très bien, merci ! Et toi ?"],
  [["MERCI"], "Avec plaisir !"],
  [["APPELLE", "PRENOM", "TON NOM"], "Je suis l'agent de cette application. Et toi, comment t'appelles-tu ?"],
  [["AIDE", "AIDER", "HELP"], "Bien sûr ! Pose ta question, j'écoute."],
  [["AU REVOIR", "BYE", "A PLUS", "BONNE NUIT"], "Au revoir ! À bientôt."],
  [["JE T'AIME", "JE T AIME"], "C'est très gentil !"],
  [["QUI ES", "QUE FAIS", "TU FAIS QUOI"], "Je lis tes signes, je reconstruis tes phrases et je te réponds."],
  [["OUI"], "Parfait !"],
  [["NON"], "D'accord, pas de souci."],
];
const RULES_EN: [string[], string][] = [
  [["HELLO", "HI", "HEY"], "Hello! How are you doing?"],
  [["HOW ARE YOU", "HOW YOU DO", "HOW DO YOU DO", "HOW ARE U"], "I'm doing great, thanks! How about you?"],
  [["THANK"], "You're welcome!"],
  [["YOUR NAME", "WHO ARE YOU"], "I'm the agent of this app. What's your name?"],
  [["HELP"], "Of course! Ask me anything."],
  [["BYE", "GOODBYE", "GOOD NIGHT", "SEE YOU"], "Goodbye! See you soon."],
  [["I LOVE YOU", "LOVE YOU"], "That's very kind!"],
  [["GOOD MORNING"], "Good morning! Hope you have a great day."],
  [["MY NAME IS", "I AM"], "Nice to meet you!"],
  [["YES"], "Perfect!"],
  [["NO"], "Alright, no problem."],
];

export function rulesReply(text: string, lang: "fr" | "en"): string {
  const up = " " + text.toUpperCase().replace(/[^A-Z' ]/g, "") + " ";
  for (const [keys, reply] of lang === "fr" ? RULES_FR : RULES_EN) {
    if (keys.some((k) => up.includes(" " + k) || up.startsWith(" " + k))) return reply;
  }
  return lang === "fr" ? `J'ai compris : "${text}". Peux-tu préciser ?` : `I understood: "${text}". Can you tell me more?`;
}

export async function fetchProviders(): Promise<ProviderInfo[]> {
  try {
    const r = await fetch("/api/chat");
    if (!r.ok) return [];
    return ((await r.json()) as { providers: ProviderInfo[] }).providers ?? [];
  } catch {
    return [];
  }
}

async function callChat(body: Record<string, unknown>): Promise<Omit<Reply, "lang">[] | null> {
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) return null;
    return ((await r.json()) as { replies: Omit<Reply, "lang">[] }).replies;
  } catch {
    return null;
  }
}

function localReply(text: string, lang: "fr" | "en", note?: string): Reply {
  return { text: rulesReply(text, lang), provider: "Local rules", model: "", seconds: 0, note, lang: lang === "fr" ? "fr-FR" : "en-US" };
}

/** One answer: the chosen AI (or the best available), local rules as the last resort. */
export async function respond(text: string, history: [string, string][], provider: ProviderId, vocab: Vocabulary, allowCloud: boolean): Promise<Reply> {
  const lang = detectLang(text, vocab);
  if (!allowCloud) return localReply(text, lang);
  const replies = await callChat({ text, lang, history, provider });
  if (!replies?.length) return localReply(text, lang, "No AI answered, so the local rules replied.");
  return { ...replies[0], lang: lang === "fr" ? "fr-FR" : "en-US" };
}

/** Same sentence sent to Groq and Gemini, answers side by side. */
export async function compare(text: string, history: [string, string][], vocab: Vocabulary): Promise<Reply[]> {
  const lang = detectLang(text, vocab);
  const replies = await callChat({ text, lang, history, compare: true });
  const tts = lang === "fr" ? "fr-FR" : "en-US";
  return replies?.length ? replies.map((r) => ({ ...r, lang: tts })) : [localReply(text, lang, "No AI answered, so the local rules replied.")];
}

export async function translate(text: string, to: "en" | "fr"): Promise<string | null> {
  try {
    const r = await fetch("/api/translate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, to }) });
    return r.ok ? ((await r.json()) as { text: string }).text : null;
  } catch {
    return null;
  }
}

export function speak(text: string, lang: string) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch { /* speech not available */ }
}
