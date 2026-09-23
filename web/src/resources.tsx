// Models and vocabulary are loaded once, the first time a page needs them.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Agent, Vocabulary } from "./lib/agent";
import { Model } from "./lib/nn";
import type { Models } from "./vision/recognizer";

export interface Resources { models: Models; vocab: Vocabulary; agent: Agent }
type State = { status: "loading" } | { status: "ready"; res: Resources } | { status: "error"; message: string };

let pending: Promise<Resources> | null = null;

function loadAll(): Promise<Resources> {
  pending ??= (async () => {
    const base = import.meta.env.BASE_URL.replace(/\/$/, "");
    const text = (p: string) => fetch(`${base}${p}`).then((r) => { if (!r.ok) throw new Error(p); return r.text(); });
    const json = <T,>(p: string) => fetch(`${base}${p}`).then((r) => { if (!r.ok) throw new Error(p); return r.json() as Promise<T>; });
    const [letters, words, letterLabels, wordLabels, fr, en] = await Promise.all([
      Model.load(`${base}/models`, "letters"), Model.load(`${base}/models`, "words"),
      json<string[]>("/models/letters_labels.json"), json<string[]>("/models/words_labels.json"),
      text("/vocab/vocab_fr.txt"), text("/vocab/vocab_en.txt"),
    ]);
    const vocab = Vocabulary.fromText(fr, en);
    return { models: { letters, words, letterLabels, wordLabels }, vocab, agent: new Agent(vocab) };
  })();
  return pending;
}

const Ctx = createContext<State>({ status: "loading" });

export function ResourcesProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    loadAll().then(
      (res) => setState({ status: "ready", res }),
      (e: unknown) => setState({ status: "error", message: String((e as Error)?.message ?? e) }),
    );
  }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}

export const useResources = () => useContext(Ctx);

