<div align="center">

# 🤟 ASL Sign Agent

**A real-time AI agent that reads American Sign Language (fingerspelling and word signs), interprets it, talks back and speaks.**

**[Try the live demo: asl-agent.vercel.app](https://asl-agent.vercel.app/)**

[![Live demo](https://img.shields.io/badge/live%20demo-asl--agent.vercel.app-6B5BFF)](https://asl-agent.vercel.app/)
![Python](https://img.shields.io/badge/python-3.11-6B5BFF)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-151833)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45-151833)
![React](https://img.shields.io/badge/React-18-151833)
[![CI](https://github.com/nazmussama19-lgtm/Asl-sign-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/nazmussama19-lgtm/Asl-sign-agent/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-6B5BFF)

</div>

<p align="center">
  <img src="docs/sign_to_text.gif" alt="Sign to Text demo: letters recognized live, interpreted and answered" width="100%">
</p>

## What it does

Sign in front of your webcam. The app recognizes the **ASL alphabet** (fingerspelling) and a set of **word signs**, rebuilds your sentence with an **interpreting agent** (word segmentation, spell correction, shorthand expansion: *"ILOVE U" → "I love you"*), **answers you** with an AI model and **reads the answer out loud**. It also turns text back into signs, gamifies practice with adaptive drills, and lets you teach it **your own signs** in 3 gestures.

```mermaid
flowchart LR
    A[Webcam] --> B[MediaPipe<br/>21 hand landmarks]
    B --> C[MLP<br/>letters]
    B --> D[Conv1D + GRU<br/>word signs]
    C --> E[Interpreting agent<br/>segment, correct, expand]
    D --> E
    E --> F[Conversation<br/>Groq, Gemini, Ollama or local rules]
    F --> G[Browser voice]
```

## Features

| | |
|---|---|
| **Sign to Text** | Real-time letter recognition (28 static signs), motion-based J and Z, word signs, live tuning sliders |
| **Interpreting agent** | Triggers itself after a pause, explains every decision, bilingual English/French, ~23k-word vocabulary, shorthand expansion |
| **Conversation and voice** | Replies with **Groq** (gpt-oss-120b, gpt-oss-20b as backup), **Gemini**, a local **Ollama** model or built-in rules, with automatic fallback. A **comparison mode** shows Groq and Gemini side by side. Replies are read by the browser voice |
| **Practice** | Gamified word challenges, streaks, **adaptive drills that target your weak letters**, personal confusion stats |
| **Personalization** | Record your own sign in 3 gestures (no retraining), fix a letter that fails for you with 5 examples (few-shot k-NN overlay) |
| **Text to Sign** | Animated word signs when known, fingerspelling otherwise, English/French translation, GIF export |
| **Results** | Accuracy and per-sign F1-score of the letter model |

## Demos

**Practice mode**: adaptive drills, streaks and personal statistics.

<p align="center"><img src="docs/practice.gif" alt="Practice mode demo" width="100%"></p>

**Text to Sign**: word signs animated, the rest fingerspelled, with GIF export.

<p align="center"><img src="docs/text_sign.gif" alt="Text to Sign demo" width="100%"></p>

## Results

| Model | Task | Accuracy |
|---|---|---|
| MLP on hand landmarks | 28 static signs (A–Z, space, delete) | **99.23 %** |
| Conv1D + GRU | 24 word signs | **86 %** |

The word-sign model is trained on the [Google ASL Signs](https://www.kaggle.com/competitions/asl-signs) dataset, which covers up to **250 signs**. We downloaded and evaluated **24 signs**; the deployed demo ships a lighter **9-sign** model to keep the app small and fast.

## Two versions

| | **Web demo** | **Full app** |
|---|---|---|
| For | trying it online, in one click | running it on your own computer |
| Link / command | **[asl-agent.vercel.app](https://asl-agent.vercel.app/)** | `streamlit run app.py` |
| Built with | React + TypeScript (`web/`) | Python + Streamlit |
| Where the video is analysed | **in your browser**: the video never leaves your computer | on your computer (Python, MediaPipe, TensorFlow) |
| Conversation | Groq and Gemini (through a serverless function), local rules as a fallback | Groq, Gemini, **Ollama** (fully offline) or local rules |
| Extras | nothing to install, works on phones | sign photos and word-sign animations when the datasets are installed, retraining notebooks |

Both versions use **the same trained models and the same interpreting agent**: the web demo is a TypeScript port, and automated tests check that it gives the same results as Python and Keras (see [`web/README.md`](web/README.md)).

## Try it online

Open **[asl-agent.vercel.app](https://asl-agent.vercel.app/)** in Chrome, Edge or Firefox, go to **Sign to text**, click **Start the camera** and allow it. The first visit downloads the hand tracker and the models (about 10 MB), then everything runs in your browser: the video is never uploaded. Settings are in the left panel (a **Settings** button on phones); J/Z detection and word signs are off by default and can be turned on there.

## Run the full app locally

Requires **Python 3.11** (TensorFlow 2.15 and MediaPipe 0.10.9). The environment takes about 1.5 to 2 GB.

```bash
git clone https://github.com/nazmussama19-lgtm/Asl-sign-agent.git
cd Asl-sign-agent
python3.11 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Letter recognition, the agent, conversation (local rules), voice, practice and personalization work out of the box: the trained models ship with the repo. The **Home** page shows what is active. To add Groq or Gemini, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the keys; for a fully offline conversation, install Ollama (below).

## Run the web demo locally

Requires **Node.js 20+**.

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

Without the Vercel functions, the conversation falls back to the local rules. `npm test` runs the model and agent tests.

## Deployment

**Web demo (Vercel, free).** Import the repository on [vercel.com](https://vercel.com), set **Root Directory** to `web` (Vercel detects Vite), and add the environment variables `GROQ_API_KEY` ([console.groq.com/keys](https://console.groq.com/keys)) and `GEMINI_API_KEY` ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). Model names can be changed with `GROQ_MODEL`, `GROQ_FAST_MODEL` and `GEMINI_MODEL`, without touching the code. Every push to `main` redeploys the site, and every pull request gets its own preview link.

**Full app (optional, Streamlit Community Cloud).** It works, but the webcam is slow there: every frame travels to a small shared server and back. The web demo is the recommended online version. If you still want it: create an app from this repository (main file `app.py`, **Python 3.11** in Advanced settings) and paste [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) into **Secrets** with your keys and a TURN relay (for example [Metered](https://www.metered.ca/stun-turn), free tier).

## Optional add-ons

<details>
<summary><b>Sign photos (chart, Text to Sign)</b></summary>

Without them, the app uses public-domain drawings from Wikimedia Commons. For real photos, download the <a href="https://www.kaggle.com/datasets/grassknoted/asl-alphabet">ASL Alphabet dataset</a> (Kaggle, ~1 GB) and put the <code>Asl_Sign_Data/</code> folder inside the repo (gitignored). The app finds it and picks the best photos automatically.
</details>

<details>
<summary><b>Word signs (up to 24 signs)</b></summary>

1. <code>pip install kaggle pyarrow</code>, put your Kaggle API token in <code>~/.kaggle/</code>, and accept the rules of the <a href="https://www.kaggle.com/competitions/asl-signs">asl-signs competition</a>.
2. <code>python download_signs_dataset.py</code>: targeted download (a few hundred MB, resumable).
3. <code>python make_word_previews.py</code>: generates the sign animations.
4. Run <code>notebooks/03_word_signs_training.ipynb</code>: trains the GRU and saves the model.
5. Turn on <b>Word signs</b> in the app sidebar.
</details>

<details>
<summary><b>Fully local conversation (Ollama)</b></summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```
Detected automatically, with no configuration. Force a model with <code>ASL_OLLAMA_MODEL=name streamlit run app.py</code>.
</details>

<details>
<summary><b>Retraining the letter model</b></summary>

With <code>Asl_Sign_Data/</code> in place, run <code>notebooks/01_letters_training_evaluation.ipynb</code> (extraction, normalization, augmentation, MLP, evaluation). The landmark CSV it produces also lets the Results page recompute its metrics live.
</details>

## Project structure

```
Asl-sign-agent/
├── app.py                     # Streamlit entry point (multipage navigation)
├── views/                     # One file per page: home, sign_to_text, practice_mode, text_to_sign, chart, results
├── ui.py                      # Visual identity, letter tiles, cached models, sign images
├── agent.py                   # Interpreting agent (segmentation, correction, reasoning log)
├── conversation.py            # Conversation engine: Groq, Gemini, Ollama, local rules, fallback, comparison
├── asl_core.py                # Normalization, sentence state machine, J/Z and thumbs-up detectors
├── word_signs.py              # Word-sign features, GRU inference, custom-sign matching
├── personal.py                # Few-shot letter personalization (k-NN overlay)
├── practice.py                # Gamified practice engine and labeled-data collection
├── sign_photos.py             # Automatic photo selection and enhancement
├── assets/vocab_{fr,en}.txt   # Frequency vocabularies (~23k words)
├── notebooks/                 # 01 letters training, 02 real-time demo, 03 word-signs training
├── tests/                     # Pytest suite (core modules, conversation engine, web models vs Keras)
├── .streamlit/                # Theme and secrets template
├── web/                       # React web demo (in-browser vision, Vercel functions for the AI)
├── tools/web_models.py        # Exports the Keras models for the web demo, with a NumPy reference
└── docs/                      # User guides (English, French) and demo GIFs
```

## Limitations

- **Fingerspelling and a closed set of word signs are not sign language translation.** ASL has a spatial grammar and non-manual features; sentence-level translation is still an open research problem.
- The letter score is measured on the dataset used for training; accuracy on new signers, lighting and cameras is lower. The Practice mode collects your own labeled samples to measure that gap.
- J and Z use a motion heuristic; a sequence model trained on trajectories is the natural next step.
- Personal samples and custom signs are stored on the machine running the app: online, they are shared between visitors and reset when the server restarts.

## Privacy

- **Web demo**: the video is analysed in your browser and never uploaded. Only the **text** of the conversation is sent to Groq or Gemini, through a serverless function that keeps the API keys secret. Personal examples, custom signs and practice statistics are stored in your browser.
- **Full app, locally with Ollama**: video, landmarks, personal samples and conversation never leave your machine.
- Personal data files of the full app are gitignored.

## Documentation

[User guide (English)](docs/GUIDE_EN.md) · [Guide utilisateur (français)](docs/GUIDE_FR.md)

## Credits

[MediaPipe](https://mediapipe.dev) · [ASL Alphabet dataset](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (GPL-2.0, not redistributed) · [Google ASL Signs](https://www.kaggle.com/competitions/asl-signs) (competition data, not redistributed) · ASL alphabet drawings: public domain, [Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:ASL_letters) (wpclipart.com) · [wordfreq](https://github.com/rspeer/wordfreq) · [Groq](https://groq.com) · [Gemini API](https://ai.google.dev) · [Ollama](https://ollama.com) · Real-signer videos linked from [SignASL.org](https://www.signasl.org)

*M2 Computer Science & Data Science project, MIT licensed.*
