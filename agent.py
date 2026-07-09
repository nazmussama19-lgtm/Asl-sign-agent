"""Agent IA local d'interpretation de l'epellation ASL (100% gratuit, hors-ligne).

Boucle d'agent : PERCEPTION (flux de lettres) -> MEMOIRE (tampon, vocabulaire FR+EN,
abreviations) -> RAISONNEMENT (nettoyage, segmentation, correction, expansion des
abreviations, detection de langue) -> ACTION (texte interprete, suggestions, journal),
avec declenchement autonome sur pause (desactivable).
"""
import os, time, threading, difflib, re
from functools import lru_cache

def _read_words(fn):
    out = []
    if os.path.exists(fn):
        with open(fn) as f:
            out = f.read().split()
    return out

def _load_vocab():
    fr = _read_words("assets/vocab_fr.txt")
    en = _read_words("assets/vocab_en.txt")
    words, rank = [], {}
    for lst in (fr, en):
        for i, w in enumerate(lst):
            if len(w) == 1 and w not in ("A", "I"):
                continue
            if w not in rank:
                rank[w] = i
                words.append(w)
    by_len = {}
    for w in words:
        by_len.setdefault(len(w), []).append(w)
    return words, rank, by_len, set(fr), set(en)

VOCAB, RANK, BY_LEN, FR_SET, EN_SET = _load_vocab()
VOCAB_SET = set(VOCAB)

# --- Abreviations conventionnelles de l'epellation (anglais + francais) ---
ABBREV_EN = {
    "U": "you", "R": "are", "UR": "your", "YR": "your", "Y": "why",
    "N": "and", "B": "be", "C": "see", "K": "ok", "OK": "ok",
    "THX": "thanks", "TY": "thank you", "PLS": "please", "PLZ": "please",
    "BC": "because", "BCS": "because", "W": "with", "WO": "without",
    "TMR": "tomorrow", "TMRW": "tomorrow", "TDY": "today", "RN": "right now",
    "MSG": "message", "NVM": "nevermind", "IDK": "i dont know",
    "BRB": "be right back", "OMW": "on my way", "ILY": "i love you",
}
ABBREV_FR = {
    "BJR": "bonjour", "SLT": "salut", "CC": "coucou", "CV": "ca va",
    "MRC": "merci", "BCP": "beaucoup", "DSL": "desole", "STP": "s'il te plait",
    "SVP": "s'il vous plait", "PK": "pourquoi", "PCQ": "parce que",
    "AJD": "aujourd'hui", "MTN": "maintenant", "TT": "tout", "TLM": "tout le monde",
    "JSP": "je sais pas", "JTM": "je t'aime", "QQN": "quelqu'un",
    "QQCH": "quelque chose", "RDV": "rendez-vous", "STV": "si tu veux",
}
ABBREV = {}
ABBREV.update(ABBREV_EN)
ABBREV.update(ABBREV_FR)

@lru_cache(maxsize=4096)
def _close(word):
    cands = []
    for L in (len(word) - 1, len(word), len(word) + 1):
        cands.extend(BY_LEN.get(L, []))
    m = difflib.get_close_matches(word, cands, n=1, cutoff=0.78)
    return m[0] if m else None

@lru_cache(maxsize=8192)
def _word_cost(w):
    BREAK = 1.6
    if w in RANK:
        c = 0.5 + RANK[w] / 8000.0
        if len(w) == 1:
            c += 2.2
        elif len(w) == 2 and RANK[w] > 1500:
            c += 2.5
        return c + BREAK
    if 4 <= len(w) <= 9:
        m = _close(w)
        if m:
            return 2.0 + RANK[m] / 8000.0 + 3.2 + BREAK
    return 4.0 + 1.6 * len(w) + BREAK

def collapse_repeats(s):
    return re.sub(r"(.)\1{2,}", r"\1\1", s)

def segment(s):
    n = len(s)
    if n == 0:
        return ""
    cost = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(max(0, i - 16), i):
            c = cost[j] + _word_cost(s[j:i])
            if c < cost[i]:
                cost[i] = c; back[i] = j
    out, i = [], n
    while i > 0:
        out.append(s[back[i]:i]); i = back[i]
    return " ".join(reversed(out))

def correct_word(w):
    if w in VOCAB_SET or len(w) < 3:
        return w, False
    m = _close(w)
    if m:
        return m, True
    return w, False

def suggest(prefix, k=3):
    p = re.sub(r"[^A-Z]", "", prefix.upper())
    if len(p) < 2:
        return []
    out = []
    for w in VOCAB:
        if w.startswith(p) and w != p:
            out.append(w)
            if len(out) >= k:
                break
    return out

def _detect_lang(words):
    fr = sum(1 for w in words if w.upper() in FR_SET and w.upper() not in EN_SET)
    en = sum(1 for w in words if w.upper() in EN_SET and w.upper() not in FR_SET)
    if fr > en:
        return "francais"
    if en > fr:
        return "anglais"
    return None

def interpret(raw):
    """Pipeline de raisonnement. Retourne (texte_interprete, journal des decisions)."""
    journal = []
    s = re.sub(r"[^A-Za-z ]", "", raw).upper().strip()
    if not s:
        return "", ["(rien a interpreter)"]
    t = collapse_repeats(s)
    if t != s:
        journal.append("Repetitions supprimees : " + s + " -> " + t)

    def expand_or_correct(w):
        if w in ABBREV:
            rep = ABBREV[w]
            journal.append("Abreviation : " + w + " -> " + rep)
            return rep.split()
        cw, changed = correct_word(w)
        if changed:
            journal.append("Correction : " + w + " -> " + cw)
        return [cw]

    words = []
    for chunk in t.split():
        if chunk in ABBREV:
            rep = ABBREV[chunk]
            journal.append("Abreviation : " + chunk + " -> " + rep)
            words.extend(rep.split())
            continue
        if chunk in VOCAB_SET:
            words.append(chunk); continue
        seg = segment(chunk)
        if seg != chunk:
            journal.append("Segmentation : " + chunk + " -> " + seg)
        for w in seg.split():
            words.extend(expand_or_correct(w))

    lang = _detect_lang(words)
    if lang:
        journal.append("Langue detectee : " + lang)

    out = [w.lower() for w in words]
    if lang == "anglais":
        out = ["I" if w == "i" else w for w in out]     # 'I' majuscule en anglais
    final = " ".join(out).strip()
    final = (final[:1].upper() + final[1:]) if final else final
    if not journal:
        journal.append("Texte deja coherent, aucune correction necessaire.")
    return final, journal

class InterpretingAgent:
    """Observe le flux, detecte les pauses, decide (si le mode auto est actif), agit."""
    def __init__(self, pause_s=5.0):
        self.pause_s = pause_s
        self.auto = True
        self.lock = threading.Lock()
        self.last_hand_t = time.time()
        self.last_interpreted_raw = None
        self.interpretation = ""
        self.journal = []
        self.suggestions = []

    def observe(self, raw_sentence, hand_present):
        now = time.time()
        with self.lock:
            if not raw_sentence.strip():
                self.last_interpreted_raw = None      # texte vide -> pret pour la phrase suivante
            if hand_present:
                self.last_hand_t = now
                last_word = raw_sentence.split(" ")[-1] if raw_sentence else ""
                self.suggestions = suggest(last_word)
            elif self.auto:
                if (now - self.last_hand_t) >= self.pause_s and raw_sentence.strip() \
                        and raw_sentence != self.last_interpreted_raw:
                    self.interpretation, self.journal = interpret(raw_sentence)
                    self.last_interpreted_raw = raw_sentence

    def interpret_now(self, raw_sentence):
        with self.lock:
            self.interpretation, self.journal = interpret(raw_sentence)
            self.last_interpreted_raw = raw_sentence
            return self.interpretation

    def state(self):
        with self.lock:
            return self.interpretation, list(self.journal), list(self.suggestions)

    def consume_interpretation(self):
        """Recupere l'interpretation courante et remet l'agent en attente (mode conversation).
        Note anti-doublon : last_interpreted_raw est CONSERVE pour que le meme texte brut ne
        puisse pas re-declencher une interpretation pendant que l'interface vide le tampon ;
        il est remis a zero par observe() des que le texte redevient vide."""
        with self.lock:
            out = self.interpretation
            self.interpretation = ""
            self.journal = []
            return out

    def get_suggestions(self):
        with self.lock:
            return list(self.suggestions)
