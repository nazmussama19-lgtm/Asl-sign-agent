# ASL Sign Agent : guide complet (français)

*English version: [GUIDE_EN.md](GUIDE_EN.md)*

Application de reconnaissance et d'interprétation de la langue des signes américaine (ASL) :
épellation de l'alphabet et signes-mots, agent d'interprétation autonome, conversation vocale
avec une IA. L'interface de l'application est en anglais ; ce guide cite donc les libellés
tels qu'ils apparaissent à l'écran.

---

## 1. Utiliser la version en ligne

Ouvrez [sign-agent.streamlit.app](https://sign-agent.streamlit.app/). Rien à installer : autorisez la caméra
quand le navigateur le demande. La page **Home** indique ce qui est actif sur ce déploiement
(modèles, IA de conversation, photos).

## 2. Installation locale (optionnelle)

Prérequis : **Python 3.11** (compatibilité TensorFlow 2.15 / MediaPipe 0.10.9). L'environnement
pèse environ 1,5 à 2 Go.

```bash
git clone https://github.com/nazmussama19-lgtm/Asl-sign-agent.git
cd Asl-sign-agent
python3.11 -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Le navigateur s'ouvre sur http://localhost:8501. Pour activer Groq ou Gemini en local, copiez
`.streamlit/secrets.toml.example` en `.streamlit/secrets.toml` et remplissez les clés.

---

## 3. Les pages

### Sign to Text : la démonstration principale

Cliquez sur **Start** sous la vidéo et autorisez la caméra. Épelez : chaque lettre stable et
sûre s'ajoute à la phrase (bandeau sous la vidéo et tuiles « Letters read live »).

**Barre latérale, section Recognition** (modifiable en direct) :
- *Confidence threshold* : certitude minimale pour accepter une lettre (0,80 par défaut).
- *Stability (frames)* : nombre d'images identiques requises (anti-clignotement).
- *Repeat delay* : temps minimal entre deux lettres (évite « AAAA »).
- *Detect J and Z (motion)* : J et Z sont des gestes, détectés par le mouvement (J part de la
  pose du I, Z trace un zigzag de l'index). Pendant un geste, les lettres sont bloquées.
- *Word signs* : reconnaissance de mots entiers signés d'un geste (désactivé par défaut).
- *Use my letter examples* : vos exemples personnels corrigent le modèle.

**Section Agent** : *Interpret automatically* déclenche l'interprétation après une pause
(~5 s sans main, réglable). Sinon, bouton **Interpret**.

**Section Conversation** :
- *AI model* : **Auto** essaie Groq (gpt-oss-120b), puis Groq rapide (gpt-oss-20b), Gemini,
  Ollama, et enfin les règles locales. Vous pouvez aussi forcer un modèle précis. Seuls les
  modèles configurés apparaissent.
- *Compare Groq and Gemini* : envoie chaque phrase aux deux et affiche les réponses côte à côte,
  avec leur temps de réponse.
- Sous chaque réponse, une ligne indique quel modèle a répondu et en combien de temps.
- Chaque visiteur dispose d'un nombre limité de réponses IA par session (40 par défaut) ;
  au-delà, les règles locales prennent le relais.

**L'agent** supprime les répétitions, segmente le flux en mots, corrige les fautes, développe
les abréviations (U → you, BJR → bonjour…), détecte la langue et note chaque décision
(dépliant *Agent reasoning*). Des suggestions de mots s'affichent pendant l'épellation :
**pouce levé** = accepter la première.

**Personalization** (sous la conversation, caméra allumée) :
- *Create a custom sign* : nommez un signe, faites le geste 3 fois, il est ensuite reconnu
  comme un mot, sans réentraînement (nécessite *Word signs*).
- *A letter doesn't work for me* : 5 exemples de votre main corrigent le modèle immédiatement.

### Practice : apprendre en jouant

Choisissez **Words** (par difficulté, mots anglais ou français) ou **Adaptive letters** (vos
lettres faibles reviennent plus souvent), cliquez **Start a new challenge**, puis signez la
lettre surlignée en cyan. Cadre vert = réussi, rouge = réessayez. La section *Your progress*
montre votre taux de réussite par lettre et vos confusions les plus fréquentes.

### Text to Sign : la traduction inverse

Tapez une phrase (anglais ou français, traduction optionnelle, internet requis). Les signes-mots
animés sont utilisés quand ils existent, les autres mots sont épelés lettre par lettre. Lecture,
pause, vitesse réglable et **export GIF**.

### ASL Chart

Les 26 lettres, chacune avec un lien *Watch* vers des vidéos de vraies personnes (SignASL.org).
Sans le dataset de photos, l'application utilise des dessins du domaine public (Wikimedia Commons).

### Results

Précision du modèle de lettres (99,23 %) et F1-score par signe. Avec le CSV de landmarks
(notebook 01), les métriques et la matrice de confusion sont recalculées en direct.
Signes-mots : 86 % sur 24 signes ; la démo embarque un modèle allégé de 9 signes.

---

## 4. Options (tout est facultatif)

**Photos des signes** : téléchargez le dataset
[ASL Alphabet](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (~1 Go) et placez le
dossier `Asl_Sign_Data/` dans le dépôt (ignoré par git).

**Signes-mots (jusqu'à 24)** :
1. `pip install kaggle pyarrow`, clé API Kaggle dans `~/.kaggle/`, et **acceptez les règles**
   de la compétition [asl-signs](https://www.kaggle.com/competitions/asl-signs).
2. `python download_signs_dataset.py` (téléchargement ciblé, reprend s'il est interrompu).
3. `python make_word_previews.py` (animations).
4. Notebook `notebooks/03_word_signs_training.ipynb` (entraînement du GRU).
5. Activez *Word signs* dans l'application.

**Ollama (IA 100 % locale)** :
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```
Détection automatique. Forcer un modèle : `ASL_OLLAMA_MODEL=nom streamlit run app.py`.

---

## 5. Dépannage

| Problème | Solution |
|---|---|
| `pip install` échoue sur mediapipe/tensorflow | Vérifiez Python **3.11** (`python --version` dans le venv) |
| La caméra ne démarre pas | Autorisez-la dans le navigateur, fermez les autres applications qui l'utilisent |
| Vidéo noire en ligne (réseau d'entreprise, 4G) | Le déploiement a besoin d'un serveur relais TURN (voir README, section Deployment) |
| Kaggle : `403 Forbidden` | Règles de la compétition non acceptées sur kaggle.com |
| L'IA ne répond pas | Vérifiez les clés dans les *secrets* ; la ligne sous la réponse indique quel modèle a répondu |
| Conversation muette | Cliquez une fois dans la page (les navigateurs bloquent l'audio avant une interaction) |
| Signes-mots inertes | *Word signs* activé ? Geste assez ample ? Modèle présent (page Home) ? |

---

## 6. Confidentialité et données

- **En local avec Ollama** : tout reste sur votre machine.
- **En ligne** : la vidéo est traitée par le serveur qui héberge l'application (Streamlit Cloud)
  et n'est pas enregistrée. Seul le **texte** de la conversation est envoyé à Groq ou Gemini
  quand ils sont utilisés.
- Les fichiers créés par l'usage (`assets/user_samples.csv`, `assets/personal_letters.csv`,
  `assets/practice_stats.json`, `assets/custom_signs.json`) contiennent des coordonnées de la main,
  jamais d'images. Ils sont écrits sur la machine qui exécute l'application et exclus de git.
  En ligne, ils sont donc partagés entre les visiteurs et effacés à chaque redémarrage du serveur.

## 7. Périmètre

Ce projet reconnaît l'**épellation** et un **vocabulaire fermé de signes-mots**. Les langues des
signes possèdent une grammaire spatiale et des composantes non manuelles : leur traduction
complète reste un problème de recherche ouvert.
