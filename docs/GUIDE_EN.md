# ASL Sign Agent: user guide (English)

*Version française : [GUIDE_FR.md](GUIDE_FR.md)*

An app that recognizes and interprets American Sign Language (ASL): alphabet fingerspelling and
word signs, an autonomous interpreting agent, and a spoken conversation with an AI.

---

## 1. Use the online version

Open the app link (see the README). Nothing to install: allow the camera when your browser asks.
The **Home** page shows what is active on this deployment (models, conversation AI, photos).

## 2. Run it locally (optional)

Requires **Python 3.11** (TensorFlow 2.15 / MediaPipe 0.10.9). The environment takes about 1.5 to 2 GB.

```bash
git clone https://github.com/nazmussama19-lgtm/Asl-sign-agent.git
cd Asl-sign-agent
python3.11 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens http://localhost:8501. To use Groq or Gemini locally, copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the keys.

---

## 3. Pages

### Sign to Text: the main demo

Click **Start** under the video and allow the camera. Fingerspell: every stable, confident letter
is added to the sentence (bar under the video and the *Letters read live* tiles).

**Sidebar, Recognition** (live settings):
- *Confidence threshold*: minimum certainty to accept a letter (0.80 by default).
- *Stability (frames)*: how many identical frames are required (prevents flicker).
- *Repeat delay*: minimum time between two letters (prevents "AAAA").
- *Detect J and Z (motion)*: J and Z are movements, detected from motion (J starts from the I pose,
  Z draws a zigzag with the index finger). Letters are paused during a movement.
- *Word signs*: recognize whole words signed with one gesture (off by default).
- *Use my letter examples*: your personal examples override the model.

**Agent**: *Interpret automatically* interprets your sentence after a pause (about 5 s without a
hand, adjustable). Otherwise, use the **Interpret** button.

**Conversation**:
- *AI model*: **Auto** tries Groq (gpt-oss-120b), then Groq fast (gpt-oss-20b), Gemini, Ollama and
  finally the local rules. You can also pick one model. Only configured models are listed.
- *Compare Groq and Gemini*: sends each sentence to both and shows the answers side by side, with
  their response time.
- Under each answer, a line tells which model replied and how long it took.
- Each visitor gets a limited number of AI replies per session (40 by default); after that the
  local rules take over.

**The agent** removes repeats, splits the stream into words, fixes typos, expands shorthand
(U → you, BJR → bonjour…), detects the language and logs every decision (*Agent reasoning*).
Word suggestions appear while you spell: **thumbs up** accepts the first one.

**Personalization** (below the conversation, camera on):
- *Create a custom sign*: name a sign, do the gesture 3 times, and it is recognized as a word,
  with no retraining (needs *Word signs*).
- *A letter doesn't work for me*: 5 examples of your hand correct the model right away.

### Practice: learn by playing

Pick **Words** (by difficulty, English or French words) or **Adaptive letters** (the letters you
miss come back more often), click **Start a new challenge**, then sign the letter highlighted in
yellow. Green frame = correct, red = try again. *Your progress* shows your success rate per letter
and the letters you mix up most.

### Text to Sign: the other direction

Type a sentence (English or French, optional translation, needs internet). Animated word signs are
used when they exist, other words are fingerspelled. Play, pause, adjustable speed and **GIF export**.

### ASL Chart

The 26 letters, each with a *Watch* link to videos of real signers (SignASL.org). Without the photo
dataset, the app uses public-domain drawings (Wikimedia Commons).

### Results

Letter model accuracy (99.23%) and F1-score per sign. With the landmark CSV (notebook 01), metrics
and the confusion matrix are recomputed live. Word signs: 86% on 24 signs; the demo ships a lighter
9-sign model.

---

## 4. Add-ons (all optional)

**Sign photos**: download the [ASL Alphabet](https://www.kaggle.com/datasets/grassknoted/asl-alphabet)
dataset (~1 GB) and put the `Asl_Sign_Data/` folder in the repo (gitignored).

**Word signs (up to 24)**:
1. `pip install kaggle pyarrow`, put your Kaggle API token in `~/.kaggle/`, and **accept the rules**
   of the [asl-signs](https://www.kaggle.com/competitions/asl-signs) competition.
2. `python download_signs_dataset.py` (targeted download, resumable).
3. `python make_word_previews.py` (animations).
4. Run `notebooks/03_word_signs_training.ipynb` (GRU training).
5. Turn on *Word signs* in the app.

**Ollama (fully local AI)**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```
Detected automatically. Force a model with `ASL_OLLAMA_MODEL=name streamlit run app.py`.

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails on mediapipe/tensorflow | Check you are on Python **3.11** (`python --version` in the venv) |
| The camera does not start | Allow it in the browser, close other apps using it |
| Black video online (work network, mobile data) | The deployment needs a TURN relay server (README, section Deployment) |
| Kaggle: `403 Forbidden` | Competition rules not accepted on kaggle.com |
| The AI does not answer | Check the keys in the secrets; the line under each answer tells which model replied |
| No sound | Click once in the page (browsers block audio before any interaction) |
| Word signs do nothing | *Word signs* on? Gesture wide enough? Model present (Home page)? |

---

## 6. Privacy and data

- **Locally with Ollama**: everything stays on your machine.
- **Online**: video frames are processed in memory by the server hosting the app (Streamlit Cloud)
  and are not recorded. Only the **text** of the conversation is sent to Groq or Gemini when they
  are used.
- Files created while using the app (`assets/user_samples.csv`, `assets/personal_letters.csv`,
  `assets/practice_stats.json`, `assets/custom_signs.json`) hold hand coordinates, never images.
  They are written on the machine running the app and gitignored. Online, they are shared between
  visitors and wiped when the server restarts.

## 7. Scope

This project recognizes **fingerspelling** and a **closed set of word signs**. Sign languages have
a spatial grammar and non-manual features: translating them fully is still an open research problem.
