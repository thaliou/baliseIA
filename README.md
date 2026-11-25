# BaliseIA – Outil de maintenance du balisage (Groupe G4 – UAM)

Challenge ATSA-ASECNA Innovation Days 2026 – Thématique 04 – Maintenance du balisage.
**Données fictives : ne pas utiliser pour la maintenance réelle. Toute recommandation doit être validée par un expert métier.**

## Fichiers

| Fichier | Rôle |
|---|---|
| `DONNEES_04_BALISAGE_MAINTENANCE.xlsx` | Fichier brut (référentiel, incidents, interventions) |
| `base/BaliseIA_base_connaissances.docx` | Base BaliseIA, sections 1 à 10 (référence de l'assistant) |
| `base/BaliseIA_complement_base_connaissances.txt` | Base BaliseIA, sections 11 à 14 (recommandations, synthèse mensuelle détaillée…) |
| `prepare_data.py` | Nettoyage, calculs, lecture de la Base, **contrôles bloquants**, écriture de `data.json` |
| `data.json` | 180 incidents, 30 équipements (calcul + valeurs figées de la Base), 14 recommandations, anomalies, écarts |
| `build_dashboard.py` | Injecte `data.json` dans le gabarit → `BaliseIA_dashboard_G4.html` |
| `BaliseIA_dashboard_G4.html` | L'outil : une seule page HTML, 6 onglets, graphiques et icônes SVG. Seule ressource externe : Bot Framework Web Chat, chargé uniquement si un token endpoint est configuré |
| `captures/` | Captures d'écran de vérification de chaque page |

## Relancer à partir des fichiers bruts

```bash
pip install pandas openpyxl
python prepare_data.py            # ou : python prepare_data.py chemin/vers/fichier.xlsx
python build_dashboard.py
```

Si un chiffre attendu diffère, `prepare_data.py` affiche l'écart et s'arrête (code de sortie 1) sans réécrire `data.json`. Deux séries de contrôles :

- **Contrôles des données** (16, inchangés) : 180 incidents, 152 pannes, 1 357,3 h, 7,7 h, MTTR 8,0 h, 136 / 44, pannes par site, Dakar 2025 = 43, pic mensuel 15, pièces, top 5, top 3 du score, 63 anomalies.
- **Contrôles de la Base** (6) : 30 lignes en section 3, équipements connus, EQ-DAK-SIM-01 score 65,2, EQ-DAK-SIM-02 MTTR 7,4 h, top 3 de la Base, REC-01 à REC-10 et REC-T1 à REC-T4.

Les écarts d'arrondi entre la Base et le recalcul sont signalés sans bloquer le script, et affichés dans la page Qualité des données :
- EQ-DAK-SIM-02, MTTR : 7,4 dans la Base, 7,5 recalculé ;
- EQ-DAK-SIM-01, score : 65,2 dans la Base, 65,3 recalculé, et 65,3 dans le texte de REC-06.

Sous Windows, si les accents s'affichent mal dans la console : `set PYTHONIOENCODING=utf-8`.

## Règles de calcul (Base BaliseIA, section 1)

1. **Doublons** : les lignes strictement identiques sont supprimées (INC-0046), ce qui donne 180 incidents.
2. **Durée valide** = numérique et ≥ 0. Les durées manquantes (INC-0031, INC-0089) et négatives (INC-0114) sont comptées dans les fréquences mais exclues des sommes, moyennes et MTTR.
3. **Panne** = incident hors `controle_periodique`.
4. **MTTR** = moyenne des durées valides des incidents clôturés.
5. **Pièces** : « aucune » n'est pas une pièce.
6. **Score de priorité** = 100 × (0,4 pannes + 0,3 criticité + 0,2 durée totale + 0,1 ancienneté), avec normalisation min-max sur les 30 équipements.
7. **Anomalies** : doublon, durée manquante, durée négative, incident long (> 24 h), non clôturé, incohérence panne / action.

## Origine des valeurs affichées

| Où | Valeur | Origine |
|---|---|---|
| Indicateurs, graphiques, alertes, « À retenir » | recalculés dans le navigateur selon le filtre de site | règles ci-dessus, identiques à `prepare_data.py` |
| Classement, score, MTTR, durée, pannes, cause principale par équipement | **valeurs figées** | Base, section 3 (jamais recalculées en JavaScript) |
| Recommandations | texte d'origine, mis en français lisible (sans majuscules techniques ni underscores) | Base, section 11 |

Chaque carte porte une icône (i) : son infobulle indique la section de la Base correspondante.

| Section | Contenu |
|---|---|
| 1 | Règles de calcul |
| 2 | Indicateurs globaux |
| 3 | Classement / score de priorité |
| 4 | Fiches équipement |
| 5 | Familles |
| 6 | Sites |
| 7 | Synthèse mensuelle |
| 8 | Causes récurrentes |
| 9 | Pièces et actions |
| 10 | Anomalies |
| 11 | Recommandations documentées |
| 12 | Synthèse mensuelle détaillée |

Contrôles affichés dans la page :

| Filtre | Résultat |
|---|---|
| Tous | 180 / 152 / 1 357 h / 7,7 h / 44 |
| Abidjan | 47 / 38 / 307 h / 6,8 h / 5, première cause « connectique / usure (8) » |
| Dakar | 73 / 59 / 21 en cours |

## Pages

Le filtre de site (Tous | Dakar | Niamey | Abidjan) s'applique à toutes les pages.

- **Accueil (cockpit)** : trois constats « À retenir » générés à partir des données filtrées, puis les 5 indicateurs. Viennent ensuite les 5 premières actions à valider, avec un bouton « Examiner », la courbe des pannes par mois et les alertes qualité (les catégories à 0 sont masquées).
- **Recommandations** : une fiche par recommandation (REC-01 à REC-10, REC-T1 à REC-T4), avec le constat, la recommandation et le statut.
  - « Valider » et « Rejeter » exigent le nom du validateur ; le n° d'OT et le commentaire sont facultatifs.
  - « Demander plus d'infos » envoie la question au chat BaliseIA.
  - Le journal de validation peut être exporté en CSV (séparateur `;`, compatible Excel).
  - Les décisions sont conservées dans le `localStorage` du navigateur. « Réinitialiser la démo » efface les décisions et le journal.
  - **Aucune action n'est déclenchée automatiquement : la décision appartient à l'expert métier.**
- **Rapports** : choisissez une période (un mois ou toute la période) et un site, puis cliquez sur « Générer le rapport ». Le rapport A4 imprimable contient :
  - une page de garde ;
  - 1. Synthèse : 3 à 5 constats rédigés automatiquement, comparés au mois précédent ;
  - 2. Indicateurs, avec l'écart ▲/▼ par rapport à la période précédente ;
  - 3. Tendance mensuelle ;
  - 4. Causes de panne et pièces remplacées ;
  - 5. Top 10 des équipements, avec les valeurs de la Base, section 3 ;
  - 6. Anomalies de la période ;
  - 7. Recommandations, avec leur statut de validation et le n° d'OT ;
  - 8. Méthode et limites.

  « Imprimer / Enregistrer en PDF » n'imprime que le rapport. Chaque page imprimée porte le pied de page « BaliseIA – Rapport généré le … – page X/Y – … ». Le bouton « Demander à BaliseIA de commenter ce rapport » envoie la demande au chat.
- **Analyses** :
  - pannes par équipement (top 10, égalités départagées par score) ;
  - pannes par site, ou par famille si un site est filtré ;
  - pannes par mois ;
  - causes de panne ;
  - pièces remplacées.
- **Équipements** : classement de la Base, avec rang global (/30), et rang dans le site quand un site est filtré. La criticité est en rouge pour un équipement critique (criticité élevée et rang ≤ 5). Un clic sur une ligne ouvre la fiche latérale, qui contient :
  - identité, score, rangs, criticité, ancienneté, MTTR et cause principale ;
  - une frise des incidents par mois et la liste des incidents ;
  - la recommandation liée, avec son statut ;
  - un bouton « Demander à BaliseIA ».
- **Qualité des données** : tableau complet des anomalies avec le traitement appliqué, et les écarts d'arrondi entre la Base et le recalcul.
- **BaliseIA** : le chat en pleine page. Sur les autres pages, le bouton rond en bas à droite ouvre le même chat dans un panneau latéral (une seule conversation).

Palette sémantique :

| Couleur | Usage |
|---|---|
| Bleu | données neutres |
| Orange | attention : pic, incident long, à valider |
| Rouge | critique : incidents en cours, équipement critique |
| Vert | validé |
| Gris | rejeté, texte secondaire |

## Brancher l'agent Copilot Studio

### Chat personnalisé (recommandé)
1. Dans Copilot Studio, ouvrez **Canaux → Application mobile** (ou « Web personnalisé »). Copiez le **token endpoint** (`https://…/powervirtualagents/botsbyschema/…/directline/token?api-version=2022-03-01-preview`). L'agent doit être en « Aucune authentification ».
2. Dans `build_dashboard.py`, remplacez la valeur de `const TOKEN_ENDPOINT = "COLLEZ_ICI_LE_TOKEN_ENDPOINT";`, puis relancez `python build_dashboard.py`.
3. La connexion suit le modèle officiel de Microsoft : `regionalchannelsettings`, puis domaine Direct Line régional, puis jeton, puis `WebChat.createDirectLine`. La page envoie ensuite l'événement `startConversation` pour afficher le message d'accueil.

Les questions suggérées et tous les boutons « Demander… » envoient la question directement au chat et ouvrent le panneau. L'indicateur « BaliseIA analyse les données… » reste affiché jusqu'au message du bot. Au bout de 90 s, il est remplacé par un message d'avertissement.

### Mode de repli (iframe)
Si `TOKEN_ENDPOINT` est vide ou si la connexion échoue, la page affiche l'iframe `COPILOT_URL` avec le bandeau « Mode iframe (mise en forme limitée) ». Dans ce mode, les questions sont copiées dans le presse-papiers.

### Depuis la page
Le bouton **Changer l'agent** du panneau de chat permet de saisir un autre token endpoint, ou une URL ou un code `<iframe>`. Ces réglages sont mémorisés dans ce navigateur, puis la page se recharge. **Agent par défaut** efface ces réglages.
