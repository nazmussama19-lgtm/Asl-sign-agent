// Sign images and links. Letters: public-domain drawings (Wikimedia Commons, wpclipart.com) shipped
// in public/signs. Word signs: videos of real signers on SignASL.org (linked, not embedded).

export const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
export const WORD_SIGNS = ["bad", "drink", "fine", "food", "go", "happy", "hello", "home", "later"];

export const letterImage = (L: string) => `${import.meta.env.BASE_URL}signs/${L.toUpperCase()}.png`;

const VIDEO_WORD: Record<string, string> = { thankyou: "thank-you" };
export const signVideo = (sign: string) => `https://www.signasl.org/sign/${VIDEO_WORD[sign] ?? sign.toLowerCase()}`;

// Words of a sentence that have their own ASL sign (port of word_signs.SIGN_SYNONYMS)
const SYNONYMS: Record<string, string[]> = {
  hello: ["hello", "hi", "bonjour", "salut", "coucou"], thankyou: ["thankyou", "thank", "thanks", "merci"],
  please: ["please", "stp", "svp"], yes: ["yes", "oui"], no: ["no", "non"],
  happy: ["happy", "heureux", "heureuse", "content", "contente"], sad: ["sad", "triste"], fine: ["fine", "bien"],
  bad: ["bad", "mauvais", "mal"], drink: ["drink", "boire", "bois"], water: ["water", "eau"],
  food: ["food", "eat", "manger", "mange", "nourriture"], like: ["like", "aime", "aimer", "adore"],
  see: ["see", "voir", "vois"], look: ["look", "regarde", "regarder"], go: ["go", "aller", "va", "vas"],
  wait: ["wait", "attends", "attendre", "attend"], sleep: ["sleep", "dormir", "dors"], home: ["home", "maison"],
  now: ["now", "maintenant"], later: ["later", "apres", "plustard"], where: ["where", "ou"], who: ["who", "qui"],
  why: ["why", "pourquoi"],
};
export const WORD_TO_SIGN: Record<string, string> = Object.fromEntries(
  Object.entries(SYNONYMS).flatMap(([sign, words]) => words.map((w) => [w.toUpperCase(), sign])),
);

/** Uppercase letters only, accents removed ("Été" -> "ETE"). */
export function cleanWord(w: string): string {
  return w.normalize("NFD").replace(/\p{Mn}/gu, "").toUpperCase().replace(/[^A-Z]/g, "");
}
