# ASL Sign Agent: web demo

The online version of the project, in React. Hand tracking (MediaPipe) and both models run **in the
visitor's browser**: the video is never uploaded, and the demo stays smooth on any connection.
Only the text of the conversation goes to a small serverless function that calls Groq or Gemini,
so the API keys never reach the browser.

The full Python app (Streamlit) is the version to run locally: see the main README.

## What runs where

| Part | Where |
|---|---|
| Webcam, MediaPipe hand tracking | browser |
| Letter model (MLP) and word-sign model (Conv1D + GRU) | browser, plain TypeScript inference (`src/lib/nn.ts`) |
| Interpreting agent (segmentation, corrections, shorthand) | browser (`src/lib/agent.ts`) |
| Personal examples, custom signs, practice stats | browser storage |
| Conversation (Groq, Gemini) and translation | Vercel functions (`api/`) |
| Voice | browser speech synthesis |

The models and the agent are ports of the Python code. Tests check that they give **the same
results**: `tools/web_models.py` exports the Keras weights with a NumPy reference (checked against
Keras in CI), `src/lib/nn.test.ts` compares the TypeScript models to it, and `src/lib/agent.test.ts`
compares the agent to the Python agent on 268 sentences.

## Develop

```bash
cd web
npm install
npm run dev        # http://localhost:5173, the conversation falls back to local rules
npm test
npm run build
```

After retraining a model, run `python tools/web_models.py` from the repository root to refresh
`public/models/` and the test fixtures.

## Deploy (Vercel)

1. Import the GitHub repository on [vercel.com](https://vercel.com) and set **Root Directory** to `web`.
2. Add the environment variables `GROQ_API_KEY` and `GEMINI_API_KEY` (optional: `GROQ_MODEL`,
   `GROQ_FAST_MODEL`, `GEMINI_MODEL`).
3. Deploy. Every push to `main` redeploys.

## Credits

ASL alphabet drawings: public domain, [Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:ASL_letters) (wpclipart.com).
Hand tracking: [MediaPipe](https://ai.google.dev/edge/mediapipe). Real-signer videos linked from [SignASL.org](https://www.signasl.org).
