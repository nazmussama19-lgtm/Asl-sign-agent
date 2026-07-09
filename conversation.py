"""Moteur de conversation de l'agent (100% gratuit, local).

Deux niveaux :
1. Regles conversationnelles FR/EN (toujours disponibles, instantanees).
2. Si Ollama tourne en local (http://localhost:11434), l'agent l'utilise via son
   API de chat, avec des consignes calibrees pour les entrees bruitees de l'epellation.
"""
import json, re, urllib.request
from functools import lru_cache
from agent import FR_SET, EN_SET

OLLAMA = "http://localhost:11434"

@lru_cache(maxsize=1)
def ollama_model():
    """Retourne le MEILLEUR modele Ollama local disponible, sinon None.
    Priorite : 1) variable d'environnement ASL_OLLAMA_MODEL si definie,
               2) taille de modele (nombre de milliards de parametres) extraite du nom."""
    import os, re
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
            s = max(sizes) * 10 if sizes else 0     # 1b=10, 3b=30, 4b=40, 7b=70, 70b=700...
            if "instruct" in n or "it" in n.split(":")[-1]:
                s += 2
            return s
        return sorted(models, key=score, reverse=True)[0]
    except Exception:
        return None

def detect_lang(text):
    words = re.findall(r"[A-Za-z']+", text.upper())
    fr = sum(1 for w in words if w in FR_SET and w not in EN_SET)
    en = sum(1 for w in words if w in EN_SET and w not in FR_SET)
    return "fr" if fr >= en and fr > 0 else "en"

# --- Regles locales (repli sans Ollama) ---
RULES_FR = [
    (("BONJOUR", "SALUT", "COUCOU", "HELLO"), "Bonjour ! Comment vas-tu ?"),
    (("CA VA", "COMMENT VAS", "COMMENT ALLEZ"), "Je vais tres bien, merci ! Et toi ?"),
    (("MERCI",), "Avec plaisir !"),
    (("APPELLE", "PRENOM", "TON NOM"), "Je suis l'agent de cette application. Et toi, comment t'appelles-tu ?"),
    (("AIDE", "AIDER", "HELP"), "Bien sur ! Pose ta question, j'ecoute."),
    (("AU REVOIR", "BYE", "A PLUS", "BONNE NUIT"), "Au revoir ! A bientot."),
    (("JE T'AIME", "JE T AIME"), "C'est tres gentil !"),
    (("QUI ES", "QUE FAIS", "TU FAIS QUOI"), "Je lis tes signes, je reconstruis tes phrases et je te reponds."),
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
        return 'J\'ai compris : "' + text + '". Peux-tu preciser ?'
    return 'I understood: "' + text + '". Can you tell me more?'

# --- Consignes calibrees : repondre au contenu, jamais faire le prof de signes ---
SYSTEM_EN = (
    "You are Nova, the warm and clever assistant of a sign-language application. "
    "The user's message comes from fingerspelling recognition: it may contain small errors, "
    "missing words or telegraphic grammar. Silently infer the intended meaning, then answer "
    "the actual question directly, naturally and helpfully, like a good friend would. "
    "Interpretation examples (never mention them): 'HOW YOU DO' means 'how are you doing?'; "
    "'WHAT TIME' means 'what time is it?'; 'U HUNGRY' means 'are you hungry?'. "
    "Hard rules: never comment on spelling, grammar or sign language; never ask the user to "
    "repeat, practice or sign anything; never describe gestures. Be engaging: answer, then "
    "optionally ask ONE short natural follow-up question. Reply in English, 1 to 3 short sentences."
)
SYSTEM_FR = (
    "Tu es Nova, l'assistant chaleureux et malin d'une application de langue des signes. "
    "Le message de l'utilisateur provient d'une reconnaissance d'epellation : petites erreurs, "
    "mots manquants ou style telegraphique possibles. Devine silencieusement le sens voulu, puis "
    "reponds directement, naturellement et utilement a la vraie question, comme un bon ami. "
    "Exemples d'interpretation (ne jamais les mentionner) : 'COMMENT TU VA' signifie "
    "'comment vas-tu ?' ; 'QUELLE HEURE' signifie 'quelle heure est-il ?' ; 'TU FAIM' signifie "
    "'as-tu faim ?'. Regles strictes : ne jamais commenter l'orthographe, la grammaire ou la "
    "langue des signes ; ne jamais demander de repeter, de s'entrainer ou de signer ; ne jamais "
    "decrire de gestes. Sois engageant : reponds, puis pose eventuellement UNE courte question "
    "naturelle. Reponds en francais, en 1 a 3 phrases courtes."
)

def _ollama_chat(text, lang, model, history):
    messages = [{"role": "system", "content": SYSTEM_FR if lang == "fr" else SYSTEM_EN}]
    for u, a in history[-4:]:
        messages.append({"role": "user", "content": u})
        messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": text})
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "15m",                       # garde le modele charge -> reponses rapides
        "options": {
            "num_predict": 150,                    # assez pour 2-3 phrases, pas de paves
            "temperature": 0.7,                    # vivant sans divaguer
            "top_p": 0.9,
            "repeat_penalty": 1.1,                 # evite les redites
        },
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("message", {}).get("content", "").strip()

def respond(text, history=None):
    """Retourne (reponse, langue_tts, moteur). Gratuit ; Ollama si present, regles sinon."""
    history = history or []
    lang = detect_lang(text)
    tts = "fr-FR" if lang == "fr" else "en-US"
    model = ollama_model()
    if model:
        try:
            out = _ollama_chat(text, lang, model, history)
            if out:
                return out, tts, "ollama (" + model + ")"
        except Exception:
            pass
    return _rules_reply(text, lang), tts, "regles locales"
