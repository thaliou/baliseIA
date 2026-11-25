# -*- coding: utf-8 -*-
"""
BaliseIA – Préparation des données (Thématique 04 – Maintenance du balisage, Groupe G4 – UAM)

Lit le fichier brut DONNEES_04_BALISAGE_MAINTENANCE.xlsx, applique les règles de
nettoyage, calcule les indicateurs, vérifie les chiffres attendus (le script
s'arrête si une valeur diffère) et écrit data.json.

Usage : python prepare_data.py [chemin_du_fichier.xlsx]
"""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pandas as pd

ICI = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ICI / "DONNEES_04_BALISAGE_MAINTENANCE.xlsx"
SORTIE = ICI / "data.json"
# Base BaliseIA (référence de l'assistant) : sections 1-10 dans le .docx, 11-14 dans le complément
BASE_DOCX = ICI / "base" / "BaliseIA_base_connaissances.docx"
BASE_COMPLEMENT = ICI / "base" / "BaliseIA_complement_base_connaissances.txt"

ANNEE_REF = 2026
CRITICITE_NUM = {"FAIBLE": 1, "MOYENNE": 2, "ELEVEE": 3}
POIDS = {"pannes": 0.4, "criticite": 0.3, "duree": 0.2, "anciennete": 0.1}
SEUIL_INCIDENT_LONG_H = 24
# Incohérences type de panne / action corrective
INCOHERENCES = {
    "lampe_defectueuse": {"sechage"},
    "alimentation": {"remplacement_lampe"},
    "humidite": {"remplacement_lampe"},
}


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------
def charger(source):
    """Charge les 3 onglets ; tolère des noms d'onglets légèrement différents."""
    feuilles = pd.read_excel(source, sheet_name=None, dtype=str)

    def trouver(mot):
        for nom, df in feuilles.items():
            if mot in nom.lower():
                return df.copy()
        raise SystemExit(f"Onglet contenant « {mot} » introuvable dans {source}")

    ref = trouver("referentiel")
    inc = trouver("incident")
    itv = trouver("intervention")
    for df in (ref, inc, itv):
        df.columns = [c.strip() for c in df.columns]
        for c in df.columns:
            df[c] = df[c].str.strip()
    return ref, inc, itv


def main():
    ref, inc_brut, itv = charger(SOURCE)
    anomalies = []

    # -----------------------------------------------------------------------
    # Règle 1 – Doublons : on supprime les lignes d'incidents strictement
    # identiques (toutes colonnes égales). On garde la première occurrence.
    # -----------------------------------------------------------------------
    masque_doublon = inc_brut.duplicated(keep="first")
    for iid in inc_brut.loc[masque_doublon, "incident_id"]:
        anomalies.append({"type": "DOUBLON", "incident_id": iid,
                          "detail": "Ligne strictement identique supprimée"})
    inc = inc_brut.loc[~masque_doublon].reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Règle 2 – Durée valide = numérique et >= 0. La colonne peut être en texte
    # (virgule décimale possible) : conversion en nombre, vide -> NaN.
    # Les durées manquantes / négatives restent dans les fréquences mais sont
    # exclues des sommes, moyennes et du MTTR (duree_valide = NaN).
    # -----------------------------------------------------------------------
    duree = pd.to_numeric(inc["duree_indisponibilite_h"].str.replace(",", ".", regex=False),
                          errors="coerce")
    inc["duree_brute"] = duree
    inc["duree_valide"] = duree.where(duree >= 0)
    for _, l in inc[duree.isna()].iterrows():
        anomalies.append({"type": "DUREE_MANQUANTE", "incident_id": l.incident_id,
                          "detail": "Durée d'indisponibilité absente"})
    for _, l in inc[duree < 0].iterrows():
        anomalies.append({"type": "DUREE_NEGATIVE", "incident_id": l.incident_id,
                          "detail": f"Durée négative ({l.duree_brute:g} h)"})
    for _, l in inc[duree > SEUIL_INCIDENT_LONG_H].iterrows():
        anomalies.append({"type": "INCIDENT_LONG", "incident_id": l.incident_id,
                          "detail": f"Durée de {l.duree_brute:g} h (> {SEUIL_INCIDENT_LONG_H} h)"})
    for _, l in inc[inc["statut"] == "EN_COURS"].iterrows():
        anomalies.append({"type": "NON_CLOTURE", "incident_id": l.incident_id,
                          "detail": "Incident toujours EN_COURS"})

    # -----------------------------------------------------------------------
    # Règle 3 – Une panne = tout incident sauf « controle_periodique ».
    # -----------------------------------------------------------------------
    inc["est_panne"] = inc["type_panne"] != "controle_periodique"

    # Fusion avec le référentiel (famille, criticité) et les interventions
    ref_cols = ref[["equipement_id", "famille", "date_installation", "criticite_simulee"]]
    fus = (inc.merge(ref_cols, on="equipement_id", how="left")
              .merge(itv[["incident_id", "date_intervention", "action_corrective", "piece_remplacee", "technicien_id"]],
                     on="incident_id", how="left"))
    fus["mois"] = fus["debut"].str[:7]

    # Règle 8 – Incohérences entre type de panne et action corrective
    for _, l in fus.iterrows():
        if l.action_corrective in INCOHERENCES.get(l.type_panne, set()):
            anomalies.append({"type": "INCOHERENCE", "incident_id": l.incident_id,
                              "detail": f"{l.type_panne} traitée par {l.action_corrective}"})

    # -----------------------------------------------------------------------
    # Indicateurs globaux
    # Règle 4 – MTTR = moyenne des durées valides des incidents CLOTURE.
    # -----------------------------------------------------------------------
    pannes = fus[fus["est_panne"]]
    cloture = fus["statut"] == "CLOTURE"
    # Règle 5 – « aucune » n'est pas une pièce
    pieces = fus.loc[fus["piece_remplacee"].str.lower() != "aucune", "piece_remplacee"].value_counts()

    # -----------------------------------------------------------------------
    # Règle 6 – Score de priorité par équipement (0-100)
    # 4 critères normalisés min-max sur les 30 équipements du référentiel.
    # -----------------------------------------------------------------------
    eq = ref[["equipement_id", "site", "famille", "localisation", "date_installation", "criticite_simulee"]].copy()
    eq["pannes"] = eq["equipement_id"].map(pannes.groupby("equipement_id").size()).fillna(0).astype(int)
    eq["criticite_num"] = eq["criticite_simulee"].map(CRITICITE_NUM)
    # Durée totale valide de tous les incidents de l'équipement
    eq["duree_totale"] = eq["equipement_id"].map(fus.groupby("equipement_id")["duree_valide"].sum()).fillna(0)
    eq["anciennete"] = ANNEE_REF - eq["date_installation"].str[:4].astype(int)
    eq["mttr"] = eq["equipement_id"].map(fus[cloture].groupby("equipement_id")["duree_valide"].mean())

    def minmax(s):
        etendue = s.max() - s.min()
        return (s - s.min()) / etendue if etendue else s * 0

    eq["score"] = (100 * (POIDS["pannes"] * minmax(eq["pannes"])
                          + POIDS["criticite"] * minmax(eq["criticite_num"])
                          + POIDS["duree"] * minmax(eq["duree_totale"])
                          + POIDS["anciennete"] * minmax(eq["anciennete"]))).round(1)

    # Règle 7 – Raison affichée
    def raison(l):
        types = pannes[pannes["equipement_id"] == l.equipement_id]["type_panne"].value_counts()
        d = f"{l.duree_totale:.1f}".replace(".", ",")
        if len(types) and types.iloc[0] >= 3:
            return f"Panne récurrente : {types.index[0]} ({types.iloc[0]})"
        if l.criticite_simulee == "ELEVEE":
            return f"Criticité élevée, {l.pannes} pannes, {d} h"
        return f"{l.pannes} pannes, {d} h d'arrêt"

    eq["raison"] = eq.apply(raison, axis=1)
    eq = eq.sort_values(["score", "pannes"], ascending=False).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Règle 2 (suite) / ÉTAPE 2 – Contrôles automatiques
    # -----------------------------------------------------------------------
    nb_par_type = pd.Series([a["type"] for a in anomalies]).value_counts().to_dict()
    pannes_mois = pannes.groupby("mois").size()
    # Top 5 : égalités départagées par score de priorité décroissant
    top5 = pannes.groupby("equipement_id").size().reset_index(name="n")
    top5["score"] = top5["equipement_id"].map(eq.set_index("equipement_id")["score"])
    top5 = top5.sort_values(["n", "score"], ascending=False).head(5)

    obtenu = {
        "incidents": len(fus),
        "pannes": len(pannes),
        "heures_totales": round(fus["duree_valide"].sum(), 1),
        "duree_moyenne": round(fus["duree_valide"].mean(), 1),
        "mttr": round(fus.loc[cloture, "duree_valide"].mean(), 1),
        "clotures": int(cloture.sum()),
        "en_cours": int((fus["statut"] == "EN_COURS").sum()),
        "pannes_par_site": pannes["site"].value_counts().to_dict(),
        "pannes_dakar_2025": int(((pannes["site"] == "DAK-SIM") & (pannes["debut"].str[:4] == "2025")).sum()),
        "max_mensuel": int(pannes_mois.max()),
        "mois_max": sorted(pannes_mois[pannes_mois == pannes_mois.max()].index),
        "pieces": pieces.to_dict(),
        # Contrôle insensible à l'ordre des ex aequo (mêmes couples équipement/pannes)
        "top5_pannes": sorted(zip(top5["equipement_id"], top5["n"].astype(int))),
        "top3_score": list(zip(eq["equipement_id"][:3], eq["score"][:3])),
        "anomalies": len(anomalies),
        "anomalies_par_type": nb_par_type,
    }
    attendu = {
        "incidents": 180, "pannes": 152, "heures_totales": 1357.3, "duree_moyenne": 7.7,
        "mttr": 8.0, "clotures": 136, "en_cours": 44,
        "pannes_par_site": {"DAK-SIM": 59, "NIM-SIM": 55, "ABJ-SIM": 38},
        "pannes_dakar_2025": 43, "max_mensuel": 15, "mois_max": ["2025-12", "2026-01"],
        "pieces": {"fusible": 40, "module": 35, "lampe": 34, "connecteur": 28},
        "top5_pannes": sorted([("EQ-DAK-SIM-06", 9), ("EQ-NIM-SIM-04", 9), ("EQ-DAK-SIM-04", 8),
                               ("EQ-ABJ-SIM-09", 7), ("EQ-NIM-SIM-10", 7)]),
        "top3_score": [("EQ-DAK-SIM-06", 78.2), ("EQ-DAK-SIM-08", 74.2), ("EQ-DAK-SIM-02", 71.7)],
        "anomalies": 63,
        "anomalies_par_type": {"DOUBLON": 1, "DUREE_MANQUANTE": 2, "DUREE_NEGATIVE": 1,
                               "INCIDENT_LONG": 6, "NON_CLOTURE": 44, "INCOHERENCE": 9},
    }
    erreurs = [f"  - {k} : attendu {attendu[k]!r}, obtenu {obtenu[k]!r}"
               for k in attendu if obtenu[k] != attendu[k]]
    if erreurs:
        print("ÉCHEC des contrôles automatiques :\n" + "\n".join(erreurs))
        sys.exit(1)
    print("Contrôles automatiques : OK (%d vérifications)" % len(attendu))

    # -----------------------------------------------------------------------
    # Base BaliseIA : valeurs de référence figées (section 3) et recommandations
    # (section 11). Le tableau de bord affiche ces valeurs telles quelles.
    # -----------------------------------------------------------------------
    base = lire_classement_base(BASE_DOCX)
    recos = lire_recommandations_base(BASE_COMPLEMENT)
    ids_ref = set(ref["equipement_id"])
    controles_base = {
        "lignes_section_3": (len(base), 30),
        "equipements_connus": (set(base) <= ids_ref, True),
        "score_EQ-DAK-SIM-01": (base["EQ-DAK-SIM-01"]["score"], 65.2),
        "mttr_EQ-DAK-SIM-02": (base["EQ-DAK-SIM-02"]["mttr"], 7.4),
        "top3_base": ([(k, v["score"]) for k, v in sorted(base.items(), key=lambda x: x[1]["rang"])[:3]],
                      [("EQ-DAK-SIM-06", 78.2), ("EQ-DAK-SIM-08", 74.2), ("EQ-DAK-SIM-02", 71.7)]),
        "recommandations": ([r["id"] for r in recos],
                            [f"REC-{i:02d}" for i in range(1, 11)] + [f"REC-T{i}" for i in range(1, 5)]),
    }
    erreurs = [f"  - {k} : attendu {a!r}, obtenu {o!r}" for k, (o, a) in controles_base.items() if o != a]
    if erreurs:
        print("ÉCHEC des contrôles de la Base BaliseIA :\n" + "\n".join(erreurs))
        sys.exit(1)
    print("Contrôles Base BaliseIA : OK (%d vérifications)" % len(controles_base))

    # Écarts (d'arrondi) entre la Base et le recalcul : signalés, non bloquants
    ecarts = []
    for l in eq.itertuples():
        b = base[l.equipement_id]
        calc = {"score": float(l.score), "mttr": None if pd.isna(l.mttr) else round(float(l.mttr), 1)}
        for champ in ("score", "mttr"):
            if calc[champ] != b[champ]:
                ecarts.append({"equipement_id": l.equipement_id, "champ": champ, "base": b[champ], "recalcul": calc[champ]})
    for r in recos:
        m = re.search(r"score ([\d.]+)/100", r["constat"])
        if r.get("equipement_id") and m and float(m.group(1)) != base[r["equipement_id"]]["score"]:
            ecarts.append({"equipement_id": r["equipement_id"], "champ": f"score cité dans {r['id']} (section 11)",
                           "base": base[r["equipement_id"]]["score"], "recalcul": float(m.group(1))})
    for e in ecarts:
        print(f"  Écart signalé : {e['equipement_id']} {e['champ']} – Base section 3 = {e['base']}, autre valeur = {e['recalcul']}")

    # Délai entre le début de l'incident et l'intervention (heures)
    fus["delai_h"] = (pd.to_datetime(fus["date_intervention"]) - pd.to_datetime(fus["debut"])).dt.total_seconds() / 3600

    # -----------------------------------------------------------------------
    # Écriture de data.json
    # -----------------------------------------------------------------------
    def nn(v):  # NaN -> None
        return None if pd.isna(v) else v

    data = {
        "meta": {
            "source": SOURCE.name,
            "periode": [fus["debut"].min()[:10], fus["debut"].max()[:10]],
            "annee_reference": ANNEE_REF,
            "note": "Données fictives – ne pas utiliser pour la maintenance réelle.",
        },
        "incidents": [{
            "incident_id": l.incident_id, "equipement_id": l.equipement_id, "site": l.site,
            "famille": l.famille, "debut": l.debut, "mois": l.mois,
            "duree": nn(round(l.duree_valide, 2) if pd.notna(l.duree_valide) else None),
            "type_panne": l.type_panne, "statut": l.statut,
            "piece_remplacee": nn(l.piece_remplacee), "technicien_id": nn(l.technicien_id),
            # Champs complémentaires : permettent au navigateur de recalculer les anomalies
            "duree_brute": nn(l.duree_brute), "action_corrective": nn(l.action_corrective),
            "delai_intervention_h": nn(round(l.delai_h, 2) if pd.notna(l.delai_h) else None),
        } for l in fus.itertuples()],
        "equipements": [{
            "rang": i + 1, "equipement_id": l.equipement_id, "site": l.site, "famille": l.famille,
            "annee_installation": int(l.date_installation[:4]),
            "criticite": l.criticite_simulee, "pannes": int(l.pannes),
            "duree_totale": round(float(l.duree_totale), 1),
            "mttr": None if pd.isna(l.mttr) else round(float(l.mttr), 1),
            "score": float(l.score), "raison": l.raison, "statut": "À valider",
            "localisation": l.localisation, "date_installation": l.date_installation,
            # Valeurs figées de la Base BaliseIA, section 3 (affichées telles quelles)
            "base": base[l.equipement_id],
        } for i, l in enumerate(eq.itertuples())],
        "recommandations": recos,
        "ecarts_base": ecarts,
        "anomalies": anomalies,
        "controles": {k: v for k, v in obtenu.items()},
    }
    SORTIE.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"{SORTIE.name} écrit : {len(data['incidents'])} incidents, "
          f"{len(data['equipements'])} équipements, {len(anomalies)} anomalies")


def lire_classement_base(chemin):
    """Section 3 de la Base : tableau commençant par la colonne « Rang »."""
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    racine = ET.fromstring(zipfile.ZipFile(chemin).read("word/document.xml"))
    for tbl in racine.iter(W + "tbl"):
        lignes = [["".join(t.text or "" for t in tc.iter(W + "t")).strip() for tc in tr.iter(W + "tc")]
                  for tr in tbl.iter(W + "tr")]
        if lignes and lignes[0][0] == "Rang":
            return {l[1]: {"rang": int(l[0]), "pannes": int(l[6]), "duree": float(l[7]), "mttr": float(l[8]),
                           "cause": l[9], "piece": l[10], "score": float(l[11])} for l in lignes[1:]}
    raise SystemExit(f"Tableau de classement (section 3) introuvable dans {chemin}")


def lire_recommandations_base(chemin):
    """Section 11 de la Base : REC-01 à REC-10 (par équipement) et REC-T1 à REC-T4 (transverses)."""
    texte = Path(chemin).read_text(encoding="utf-8")
    recos = []
    for m in re.finditer(r"^(REC-\d+) – (EQ-[A-Z]+-SIM-\d+) \(([A-Z_]+), ([A-Z]+-SIM) (SECTEUR-\d+)\)\s*\n"
                         r"Constat : (.+)\nRecommandation : (.+)\nStatut : (.+)$", texte, re.M):
        recos.append({"id": m[1], "equipement_id": m[2], "famille": m[3], "site": m[4], "localisation": m[5],
                      "titre": m[2], "constat": m[6].strip(), "recommandation": m[7].strip(), "statut_base": "A_VALIDER"})
    for m in re.finditer(r"^(REC-T\d+) – (.+?)\. Constat : (.+?) Recommandation : (.+?) Statut : (\w+)\.?\s*$", texte, re.M):
        recos.append({"id": m[1], "equipement_id": None, "famille": None, "site": None, "localisation": None,
                      "titre": m[2], "constat": m[3].strip(), "recommandation": m[4].strip(), "statut_base": m[5]})
    return recos


if __name__ == "__main__":
    main()
