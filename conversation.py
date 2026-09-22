"""Conversation engine: the agent answers the sentence the user just signed.

Five "brains", tried in this order in Auto mode:
1. Groq  - openai/gpt-oss-120b   (cloud, needs GROQ_API_KEY)
2. Groq  - openai/gpt-oss-20b    (cloud, same key, separate quota -> first fallback)
3. Gemini                        (cloud, needs GEMINI_API_KEY)
4. Ollama                        (local, if a model is running on localhost:11434)
5. Local rules                   (always available, instant)

A provider that is not configured is simply skipped; a provider that fails (rate limit,
timeout, network) hands over to the next one, so the demo never breaks.
Groq and Gemini both expose an OpenAI-compatible endpoint, so no extra SDK is needed.
"""
import json, os, re, time, urllib.error, urllib.request
from dataclasses import dataclass
from functools import lru_cache
from agent import FR_SET, EN_SET

OLLAMA = "http://localhost:11434"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "groq_fast": "openai/gpt-oss-20b",
    "gemini": "gemini-3.8-flash",
}
AUTO_ORDER = ["groq", "groq_fast", "gemini", "ollama", "rules"]
LABELS = {
    "auto": "Auto (best available)",
    "groq": "Groq",
    "groq_fast": "Groq (fast)",
    "gemini": "Gemini",
    "ollama": "Ollama (local)",
    "rules": "Local rules",
}
CLOUD = {"groq", "groq_fast", "gemini"}
TIMEOUT_S = 12
MAX_REPLY_TOKENS = 300          # includes the model's short reasoning; replies stay 1-3 sentences


@dataclass
class Reply:
    text: str
    lang: str            # browser speech code: "fr-FR" or "en-US"
    provider: str        # provider id that actually answered
    model: str           # model name ("" for local rules)
    seconds: float
    note: str = ""       # e.g. "Groq unavailable, answered by Gemini"

    @property
    def engine(self):
        name = LABELS.get(self.provider, self.provider)
        return name + (" (" + self.model + ")" if self.model else "")


# ---------------- Settings (Streamlit secrets or environment variables) ----------------
def setting(name, default=""):
    """Read a setting from the environment first, then from Streamlit secrets."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def model_for(provider):
    if provider == "ollama":
        return ollama_model() or ""
    if provider == "rules":
        return ""
    env = {"groq": "GROQ_MODEL", "groq_fast": "GROQ_FAST_MODEL", "gemini": "GEMINI_MODEL"}[provider]
    return setting(env, DEFAULT_MODELS[provider])


@lru_cache(maxsize=1)
def ollama_model():
    """Best local Ollama model available, or None.
    Priority: ASL_OLLAMA_MODEL if set, then the largest model (parameter count parsed from the name)."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=0.5) as r:
            models = [m["name"] for m in json.loads(r.read().decode()).get("models", [])]
        if not models:
            return None
        forced = os.environ.get("ASL_OLLAMA_MODEL", "").strip()
        if forced:
            for m in models:
                if m == forced or m.startswith(forced):
                    return m
        def score(name):
            n = name.lower()
            sizes = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)b", n)]
            s = max(sizes) * 10 if sizes else 0     # 1b=10, 3b=30, 7b=70, 70b=700...
            if "instruct" in n or "it" in n.split(":")[-1]:
                s += 2
            return s
        return sorted(models, key=score, reverse=True)[0]
    except Exception:
        return None


def is_available(provider):
    if provider in ("groq", "groq_fast"):
        return bool(setting("GROQ_API_KEY"))
    if provider == "gemini":
        return bool(setting("GEMINI_API_KEY"))
    if provider == "ollama":
        return ollama_model() is not None
    return provider == "rules"


def available_providers():
    """Provider ids worth showing in the menu: Auto + every configured brain."""
    return ["auto"] + [p for p in AUTO_ORDER if is_available(p)]


# ---------------- Language ----------------
def detect_lang(text):
    words = re.findall(r"[A-Za-z']+", text.upper())
    fr = sum(1 for w in words if w in FR_SET and w not in EN_SET)
    en = sum(1 for w in words if w in EN_SET and w not in FR_SET)
    return "fr" if fr >= en and fr > 0 else "en"


# ---------------- Local rules (always available) ----------------
RULES_FR = [
    (("BONJOUR", "SALUT", "COUCOU", "HELLO"), "Bonjour ! Comment vas-tu ?"),
    (("CA VA", "COMMENT VAS", "COMMENT ALLEZ"), "Je vais très bien, merci ! Et toi ?"),
    (("MERCI",), "Avec plaisir !"),
    (("APPELLE", "PRENOM", "TON NOM"), "Je suis l'agent de cette application. Et toi, comment t'appelles-tu ?"),
    (("AIDE", "AIDER", "HELP"), "Bien sûr ! Pose ta question, j'écoute."),
    (("AU REVOIR", "BYE", "A PLUS", "BONNE NUIT"), "Au revoir ! À bientôt."),
    (("JE T'AIME", "JE T AIME"), "C'est très gentil !"),
    (("QUI ES", "QUE FAIS", "TU FAIS QUOI"), "Je lis tes signes, je reconstruis tes phrases et je te réponds."),
    (("OUI",), "Parfait !"),
    (("NON",), "D'accord, pas de souci."),
]
RULES_EN = [
    (("HELLO", "HI", "HEY"), "Hello! How are you doing?"),
    (("HOW ARE YOU", "HOW YOU DO", "HOW DO YOU DO", "HOW ARE U"), "I'm doing great, thanks! How about you?"),
    (("THANK",), "You're welcome!"),
    (("YOUR NAME", "WHO ARE YOU"), "I'm the agent of this app. What's your name?"),
    (("HELP",), "Of course! Ask me anything."),
    (("BYE", "GOODBYE", "GOOD NIGHT", "SEE YOU"), "Goodbye! See you soon."),
    (("I LOVE YOU", "LOVE YOU"), "That's very kind!"),
    (("GOOD MORNING",), "Good morning! Hope you have a great day."),
    (("MY NAME IS", "I AM"), "Nice to meet you!"),
    (("YES",), "Perfect!"),
    (("NO",), "Alright, no problem."),
]


def _rules_reply(text, lang):
    up = " " + re.sub(r"[^A-Z' ]", "", text.upper()) + " "
    for keys, reply in (RULES_FR if lang == "fr" else RULES_EN):
        for k in keys:
            if " " + k in up or up.startswith(" " + k):
                return reply
    if lang == "fr":
        return 'J\'ai compris : "' + text + '". Peux-tu préciser ?'
    return 'I understood: "' + text + '". Can you tell me more?'


# ---------------- Prompts: answer the content, never act as a signing teacher ----------------
SYSTEM_EN = (
    "You are Nova, the warm and clever assistant of a sign-language application. "
    "The user's message comes from fingerspelling recognition: it may contain small errors, "
    "missing words or telegraphic grammar. Silently infer the intended meaning, then answer "
    "the actual question directly, naturally and helpfully, like a good friend would. "
    "Interpretation examples (never mention them): 'HOW YOU DO' means 'how are you doing?'; "
    "'WHAT TIME' means 'what time is it?'; 'U HUNGRY' means 'are you hungry?'. "
    "Hard rules: never comment on spelling, grammar or sign language; never ask the user to "
    "repeat, practice or sign anything; never describe gestures. Be engaging: answer, then "
    "optionally ask ONE short natural follow-up question. Reply in English, 1 to 3 short sentences, "
    "plain text without markdown."
)
SYSTEM_FR = (
    "Tu es Nova, l'assistant chaleureux et malin d'une application de langue des signes. "
    "Le message de l'utilisateur provient d'une reconnaissance d'épellation : petites erreurs, "
    "mots manquants ou style télégraphique possibles. Devine silencieusement le sens voulu, puis "
    "réponds directement, naturellement et utilement à la vraie question, comme un bon ami. "
    "Exemples d'interprétation (ne jamais les mentionner) : 'COMMENT TU VA' signifie "
    "'comment vas-tu ?' ; 'QUELLE HEURE' signifie 'quelle heure est-il ?' ; 'TU FAIM' signifie "
    "'as-tu faim ?'. Règles strictes : ne jamais commenter l'orthographe, la grammaire ou la "
    "langue des signes ; ne jamais demander de répéter, de s'entraîner ou de signer ; ne jamais "
    "décrire de gestes. Sois engageant : réponds, puis pose éventuellement UNE courte question "
    "naturelle. Réponds en français, en 1 à 3 phrases courtes, en texte brut sans markdown."
)


def _messages(text, lang, history):
    messages = [{"role": "system", "content": SYSTEM_FR if lang == "fr" else SYSTEM_EN}]
    for u, a in history[-4:]:
        messages.append({"role": "user", "content": u})
        messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": text})
    return messages


def _post_json(url, payload, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _openai_compatible(url, key, model, messages, extra):
    """Chat completion on an OpenAI-compatible endpoint (Groq, Gemini)."""
    payload = {"model": model, "messages": messages, "temperature": 0.7,
               "max_tokens": MAX_REPLY_TOKENS, **extra}
    headers = {"Authorization": "Bearer " + key}
    try:
        data = _post_json(url, payload, headers, TIMEOUT_S)
    except urllib.error.HTTPError as e:
        if e.code == 400 and extra:        # a tuning option the model refuses: retry without it
            payload = {k: v for k, v in payload.items() if k not in extra}
            data = _post_json(url, payload, headers, TIMEOUT_S)
        else:
            raise
    return (data["choices"][0]["message"].get("content") or "").strip()


def _ollama_chat(model, messages):
    payload = {
        "model": model, "messages": messages, "stream": False,
        "keep_alive": "15m",                        # keeps the model loaded -> fast replies
        "options": {"num_predict": 150, "temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1},
    }
    data = _post_json(OLLAMA + "/api/chat", payload, {}, 30)
    return data.get("message", {}).get("content", "").strip()


def _call(provider, messages):
    model = model_for(provider)
    if provider in ("groq", "groq_fast"):
        # gpt-oss models reason before answering: keep it short and out of the reply
        return model, _openai_compatible(GROQ_URL, setting("GROQ_API_KEY"), model, messages,
                                         {"reasoning_effort": "low", "include_reasoning": False})
    if provider == "gemini":
        return model, _openai_compatible(GEMINI_URL, setting("GEMINI_API_KEY"), model, messages,
                                         {"reasoning_effort": "low"})
    if provider == "ollama":
        return model, _ollama_chat(model, messages)
    raise ValueError("unknown provider " + provider)


def respond(text, history=None, provider="auto", allow_cloud=True):
    """Answer `text`. `provider` is "auto" or a provider id; on failure the next brain answers.
    `allow_cloud=False` skips Groq/Gemini (used once a visitor reaches the session limit)."""
    history = history or []
    lang = detect_lang(text)
    tts = "fr-FR" if lang == "fr" else "en-US"
    messages = _messages(text, lang, history)

    chain = AUTO_ORDER if provider == "auto" else [provider] + [p for p in AUTO_ORDER if p != provider]
    skipped = []
    for p in chain:
        if p == "rules":
            break
        if (p in CLOUD and not allow_cloud) or not is_available(p):
            continue
        t0 = time.perf_counter()
        try:
            model, out = _call(p, messages)
        except Exception:
            skipped.append(p)
            continue
        if out:
            note = _fallback_note(provider, skipped, p)
            return Reply(out, tts, p, model, time.perf_counter() - t0, note)
        skipped.append(p)

    t0 = time.perf_counter()
    out = _rules_reply(text, lang)
    return Reply(out, tts, "rules", "", time.perf_counter() - t0, _fallback_note(provider, skipped, "rules"))


def _fallback_note(requested, skipped, used):
    if requested != "auto" and requested != used:
        return LABELS.get(requested, requested) + " did not answer, so " + LABELS[used] + " replied."
    if skipped:
        return ", ".join(LABELS.get(s, s) for s in skipped) + " did not answer, so " + LABELS[used] + " replied."
    return ""


def compare(text, history=None, providers=("groq", "gemini")):
    """Same sentence sent to several brains, no fallback: lets you compare them side by side."""
    history = history or []
    lang = detect_lang(text)
    tts = "fr-FR" if lang == "fr" else "en-US"
    messages = _messages(text, lang, history)
    out = []
    for p in providers:
        if not is_available(p):
            continue
        t0 = time.perf_counter()
        try:
            model, reply = _call(p, messages)
            out.append(Reply(reply or "(empty reply)", tts, p, model, time.perf_counter() - t0))
        except Exception as e:
            out.append(Reply("", tts, p, model_for(p), time.perf_counter() - t0,
                             "No answer (" + _short_error(e) + ")"))
    return out


def _short_error(e):
    if isinstance(e, urllib.error.HTTPError):
        return "rate limit reached" if e.code == 429 else "HTTP " + str(e.code)
    if isinstance(e, TimeoutError) or "timed out" in str(e):
        return "timeout"
    return type(e).__name__
