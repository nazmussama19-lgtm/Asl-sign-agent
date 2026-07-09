"""Telechargement CIBLE du dataset Google ASL Signs (Kaggle, competition asl-signs).

On ne recupere PAS les 50 Go : uniquement les sequences des signes choisis
(~60 sequences par signe par defaut, soit quelques centaines de Mo).

Prerequis (une fois) :
    pip install kaggle pyarrow
    Cle API Kaggle dans ~/.kaggle/kaggle.json (kaggle.com -> Settings -> Create New Token)
    Accepter les regles de la competition : https://www.kaggle.com/competitions/asl-signs

Usage :
    python download_signs_dataset.py
Sortie :
    data_signs/subset.csv           (sequence -> signe)
    data_signs/raw/<seq_id>.parquet (landmarks de chaque sequence)
"""
import os, zipfile, random, concurrent.futures as cf

# Signes conversationnels utiles + reproductibles principalement avec les mains
SIGNS = ["hello", "thankyou", "please", "yes", "no", "happy", "sad", "fine", "bad",
         "drink", "water", "food", "like", "see", "look", "go", "wait", "sleep",
         "home", "now", "later", "where", "who", "why"]
PER_SIGN = 60          # sequences par signe (augmenter = meilleur modele, telechargement plus long)
OUT = "data_signs"

def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    import pandas as pd
    api = KaggleApi(); api.authenticate()
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

    # 1) index des sequences
    idx_csv = os.path.join(OUT, "train.csv")
    if not os.path.exists(idx_csv):
        print("Telechargement de l'index (train.csv)...")
        api.competition_download_file("asl-signs", "train.csv", path=OUT)
        z = os.path.join(OUT, "train.csv.zip")
        if os.path.exists(z):
            with zipfile.ZipFile(z) as f: f.extractall(OUT)
            os.remove(z)
    df = pd.read_csv(idx_csv)
    print("Index :", len(df), "sequences,", df["sign"].nunique(), "signes")

    # 2) sous-ensemble equilibre des signes choisis
    # (boucle explicite : robuste a toutes les versions de pandas,
    #  contrairement a groupby().apply() qui peut retirer la colonne 'sign')
    random.seed(42)
    parts = []
    for sign, g in df[df["sign"].isin(SIGNS)].groupby("sign"):
        parts.append(g.sample(min(PER_SIGN, len(g)), random_state=42))
    subset = pd.concat(parts).reset_index(drop=True)
    missing = sorted(set(SIGNS) - set(subset["sign"].unique()))
    if missing:
        print("ATTENTION - signes absents du dataset :", missing)
    subset.to_csv(os.path.join(OUT, "subset.csv"), index=False)
    print("Sous-ensemble :", len(subset), "sequences a telecharger")

    # 3) telechargement parallele, avec reprise
    def fetch(row):
        seq_id = row.sequence_id
        dest = os.path.join(OUT, "raw", f"{seq_id}.parquet")
        if os.path.exists(dest):
            return "skip"
        try:
            api.competition_download_file("asl-signs", row.path, path=os.path.join(OUT, "raw"))
            base = os.path.basename(row.path)
            got = os.path.join(OUT, "raw", base)
            gz = got + ".zip"
            if os.path.exists(gz):
                with zipfile.ZipFile(gz) as f: f.extractall(os.path.join(OUT, "raw"))
                os.remove(gz)
            if os.path.exists(got):
                os.replace(got, dest)
            return "ok"
        except Exception as e:
            return "err:" + str(e)[:60]

    done = 0
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(fetch, subset.itertuples()):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(subset)}")
    print("Termine. Fichiers dans", os.path.join(OUT, "raw"))
    print("Etape suivante : ouvrir le notebook 03_entrainement_signes_mots.ipynb")

if __name__ == "__main__":
    main()
