# 🤟 ASL Sign Agent — Guide complet (français)

Application de reconnaissance et d'interprétation de la langue des signes américaine (ASL) :
épellation de l'alphabet + signes-mots, agent d'interprétation autonome, conversation vocale.
100 % local, 100 % gratuit — aucune image ne quitte votre machine.

---

## 1. Installation (2 minutes)

Prérequis : **Python 3.11** (compatibilité TensorFlow 2.15 / MediaPipe 0.10.9). Sur Ubuntu :

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt update
sudo apt install -y python3.11 python3.11-venv
```

Puis :

```bash
git clone https://github.com/YOUR_USERNAME/asl-sign-agent.git
cd asl-sign-agent
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements_app.txt
streamlit run app.py
```

Le navigateur s'ouvre sur http://localhost:8501. La page **Accueil** affiche un panneau
« Démarrage » qui vous dit exactement ce qui est prêt et ce qui manque.

Tout fonctionne d'emblée : reconnaissance des lettres, agent, conversation, voix,
entraînement, personnalisation (les modèles entraînés sont fournis avec le dépôt).

---

## 2. Les pages

### ✋ Sign to Text — la démonstration principale

Lancez la caméra (bouton START, autorisez l'accès). Épelez : chaque lettre stable et
confiante s'ajoute à la phrase (barre noire sous la vidéo).

**Réglages (barre latérale)** — modifiables en direct :
- *Seuil de confiance* : minimum de certitude pour accepter une lettre (0,80 par défaut).
- *Stabilité* : nombre d'images identiques requises (anti-clignotement).
- *Délai anti-répétition* : temps minimal entre deux lettres (anti « AAAA »).
- *Détection J/Z* : J et Z sont des gestes — détectés par le mouvement (J part de la pose
  du I ; Z trace un zigzag de l'index). Pendant un geste, les lettres sont bloquées.
- *Interprétation automatique* : après ~5 s sans main (réglable, désactivable), l'agent
  interprète tout seul. Sinon, bouton **Interpréter**.
- *Mode conversation* + *Lecture vocale* : l'agent répond dans un fil de discussion et
  lit sa réponse (voix du navigateur).

**L'agent** : il supprime les répétitions, segmente le flux en mots, corrige les erreurs,
développe les abréviations (U → you, BJR → bonjour...), détecte la langue — et journalise
chaque décision (dépliant « Journal de l'agent »). Des **suggestions de mots** s'affichent
pendant l'épellation : **pouce levé** = accepter la première.

**Signes fonctionnels** : le signe *space* ajoute une espace, *del* efface. Boutons
équivalents sous le panneau (Espace / Effacer / Tout).

**Niveau supérieur (barre latérale)** :
- *Signes-mots* (case décochée par défaut) : signez un mot entier d'un geste ample
  (hello, thankyou, please...). Désactivée, le comportement lettres est strictement inchangé.
- *Créer un signe personnalisé* : nommez un signe, faites le geste 3 fois → reconnu
  ensuite comme un mot, sans réentraînement.
- *Cette lettre ne marche pas chez moi* : 5 exemples de votre main corrigent le modèle
  immédiatement (k-NN local).
- *Apprendre les signes* (bas de page) : chaque lettre/signe avec son image ou animation,
  un conseil, et un lien « vidéo réelle » (SignASL.org).

### 🎮 Entraînement — apprendre en jouant

Choisissez le mode (**Mots** par difficulté FR/EN, ou **Lettres adaptatives** — vos lettres
faibles reviennent plus souvent), cliquez *Démarrer*, et signez la lettre qui pulse.
Cadre vert = réussi, rouge = réessayez. Score avec multiplicateur de série, vitesse en
lettres/minute, célébration et enchaînement automatique. La section **Mes statistiques**
montre votre taux de réussite par lettre et vos confusions personnelles (persistant).
Chaque tentative alimente une collecte locale d'échantillons étiquetés
(`assets/user_samples.csv`) — base de la personnalisation et de l'évaluation inter-personnes.

### ⌨️ Text to Sign — la traduction inverse

Tapez une phrase (FR ou EN, traduction FR↔EN optionnelle — nécessite internet).
Rendu **hybride** : signes-mots animés quand ils existent, épellation en photos réelles
sinon, avec la phrase surlignée élément par élément. Vitesse réglable, lecture/pause,
et **export GIF animé** à partager.

### 🔤 Charte ASL

Les 26 lettres en photos réelles (sélectionnées et améliorées automatiquement depuis le
dataset) + les signes-mots en animations, chacun avec un lien « Vidéo réelle » vers de
vraies personnes qui signent.

### 📊 Résultats

Métriques calculées en direct depuis le modèle : précision, matrice de confusion, F1 par
lettre — avec une note honnête : ces chiffres sont mesurés « en distribution ».
(Nécessite le CSV de landmarks — voir §3.)

---

## 3. Options (tout est facultatif)

**Images des signes** : téléchargez le dataset
[ASL Alphabet](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (~1 Go) et placez
le dossier `Asl_Sign_Data/` dans le dépôt (ignoré par git). Active : Charte, photos de
Text to Sign, page Résultats après extraction (notebook 01).

**Signes-mots (jusqu'à 24)** :
1. `pip install kaggle pyarrow` ; clé API Kaggle dans `~/.kaggle/` ; **accepter les
   règles** de la compétition [asl-signs](https://www.kaggle.com/competitions/asl-signs).
2. `python download_signs_dataset.py` (téléchargement ciblé, reprend s'il est interrompu).
3. `python make_word_previews.py` (animations).
4. Notebook `notebooks/03_entrainement_signes_mots.ipynb` (entraînement GRU, **évaluation
   sur signeurs jamais vus**) → produit le modèle.
5. Cochez *Signes-mots* dans l'app.

**Ollama (conversation plus riche)** :
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b     # léger ; qwen2.5:3b si vous avez de la RAM disponible
```
Détection automatique. Forcer un modèle : `ASL_OLLAMA_MODEL=nom streamlit run app.py`.
Sans Ollama : règles conversationnelles locales (instantanées).

---

## 4. Dépannage

| Problème | Solution |
|---|---|
| `pip install` échoue sur mediapipe/tensorflow | Vérifiez Python **3.11** (`python --version` dans le venv) |
| La caméra ne s'ouvre pas | Autorisez-la dans le navigateur ; fermez les autres apps qui l'utilisent ; session graphique requise |
| « Modèle introuvable » | `asl_mediapipe_mlp_model.h5` et `labels.json` doivent être à côté de `app.py` |
| Kaggle : `403 Forbidden` | Règles de la compétition non acceptées sur kaggle.com |
| Page Résultats vide | Elle nécessite `asl_mediapipe_keypoints_dataset.csv` (notebook 01) |
| Conversation muette | Cliquez une fois dans la page (les navigateurs bloquent l'audio avant interaction) |
| Signes-mots inertes | Case *Signes-mots* cochée ? Geste assez ample ? Modèle présent (panneau Démarrage) ? |

---

## 5. Confidentialité et données

Tout s'exécute localement. Les fichiers créés par l'usage — `assets/user_samples.csv`
(échantillons d'entraînement), `assets/personal_letters.csv` (exemples personnels),
`assets/practice_stats.json` (statistiques), `assets/custom_signs.json` (signes créés) —
restent sur votre machine et sont exclus de git par défaut. Boutons de réinitialisation
dans l'app.

---

## 6. Périmètre (honnêteté)

Ce projet reconnaît l'**épellation** et un **vocabulaire fermé de signes-mots**. Les
langues des signes possèdent une grammaire spatiale et des composantes non-manuelles :
leur traduction complète reste un problème de recherche ouvert. Ce périmètre est assumé
dans l'application comme dans le rapport.
