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

- **Contrôles de la Base corrigée** (5) : EQ-DAK-SIM-08 sans cause dominante, EQ-DAK-SIM-01 à 65,2, REC-06 citant 65,2, REC-T1 citant « 30 pannes sur 152 (20 %) », et cohérence de score et de cause entre chaque recommandation et la section 3.

**Base corrigée : une seule source.** Le score et la cause principale de chaque équipement viennent de `data.json` et sont identiques partout : tableaux, fiches, accueil, rapport. Corrections appliquées, toutes listées dans la page Qualité des données :
- **Cause principale.** Quand chaque type de panne n'apparaît qu'une fois, la cause devient « Aucune cause dominante ». Cela concerne EQ-DAK-SIM-08, EQ-ABJ-SIM-06, EQ-ABJ-SIM-03, EQ-NIM-SIM-01, EQ-NIM-SIM-09, EQ-ABJ-SIM-02 et EQ-DAK-SIM-05. Pour les égalités à 2 ou 3 pannes, le choix de la Base est conservé.
- **Score dans REC-06.** Le texte indiquait 65,3 ; il est aligné sur la section 3 (65,2).
- **Part de la cause indéterminée dans REC-T1.** « 30 incidents sur 180 (16,7 %) » devient « 30 pannes sur 152 (20 %) ».
- **Écarts d'arrondi avec le recalcul** : la valeur de la Base est conservée.
  - EQ-DAK-SIM-02, MTTR : 7,4 dans la Base, 7,5 recalculé ;
  - EQ-DAK-SIM-01, score : 65,2 dans la Base, 65,3 recalculé.

Les textes de la Base sont accordés automatiquement : 0 devient « aucun incident », et 1 donne « 1 incident ».

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
  - **Cartes allégées.** Chaque carte affiche le constat, la recommandation, le statut, et deux boutons : « Décider » et « Demander plus d'infos ».
    - « Décider » déplie le formulaire : nom du validateur, commentaire, Valider, Rejeter, Annuler.
    - Ouverte par « Examiner », une carte a son formulaire déjà déplié.
  - **Ordre de travail.** Une recommandation validée, y compris transverse, propose « Générer l'ordre de travail ».
    - Le numéro suit la série OT-2026-001, 002… ; le compteur est conservé dans le navigateur, et « Réinitialiser la démo » le remet à 001.
    - L'OT s'ouvre dans une fiche d'intervention A4 imprimable : équipement, constat, action, pièces à préparer, champs à remplir, validation et signatures.
    - La pastille de la carte devient « Validée · OT-2026-00x ».
    - Le journal reçoit une ligne « OT généré », sa colonne N° OT se remplit, et l'export CSV inclut le numéro.
    - « Envoyer au chef d'équipe » prépare un e-mail : son objet suit le format « OT – équipement – action », et le corps contient le résumé.
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

  « Imprimer / Enregistrer en PDF » n'imprime que le rapport. Sauts de page uniquement après la page de garde, puis avant les sections 5, 6 et 7. Le rapport « Toute la période / Tous » fait 7 pages, « 2025-12 / Tous » en fait 6. Les incidents non clôturés sont regroupés sur une seule ligne. Dans la fenêtre d'impression, décochez « En-têtes et pieds de page ». Chaque page imprimée porte le pied de page « BaliseIA – Rapport généré le … – page X/Y – … ». Le bouton « Demander à BaliseIA de commenter ce rapport » envoie la demande au chat.
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
- **BaliseIA** : le chat en pleine page. L'en-tête du chat indique l'état de la connexion : point vert « En ligne » (Web Chat connecté), point orange « Mode iframe » (repli), point gris « Connexion… » (tentative en cours). Sur les autres pages, le bouton rond en bas à droite ouvre le même chat dans un panneau latéral (une seule conversation).

Palette sémantique :

| Couleur | Usage |
|---|---|
| Bleu | données neutres |
| Orange | attention : pic, incident long, à valider |
| Rouge | critique : incidents en cours, équipement critique |
| Vert | validé |
| Gris | rejeté, texte secondaire |

## Partager la page sans le secret

```bash
python build_dashboard.py --partage
```

Cette commande produit `BaliseIA_dashboard_G4_partage.html`, le fichier à diffuser.
- Il est identique à la page principale, sauf qu'il **ne contient pas le secret** : `directline_secret.txt` n'est jamais lu, et un contrôle bloque la génération si le secret s'y retrouvait.
- Le chat passe par l'iframe Copilot Studio de l'agent BaliseIA v2, qui fonctionne sans connexion. Son bandeau interne est masqué.
- Les questions suggérées sont alors copiées dans le presse-papiers : collez-les avec Ctrl+V.
- `BaliseIA_dashboard_G4.html` (avec le secret) reste pour un usage local uniquement.

## Brancher l'agent Copilot Studio (secret Direct Line)

> **Secret de démonstration : ne publiez pas le HTML généré, ne le versionnez pas, et régénérez le secret après l'événement.**
> Le secret est visible par toute personne qui ouvre la page.
> `BaliseIA_dashboard_G4.html` et `directline_secret.txt` sont listés dans `.gitignore`, et le HTML a été retiré du suivi git.

1. Dans Copilot Studio, ouvrez **Paramètres → Sécurité → Sécurité web**, ou **Canaux → Direct Line**, puis copiez le **Secret 1**.
2. Collez-le de l'une de ces deux façons :
   - **(recommandé)** dans un fichier `directline_secret.txt`, à côté de `build_dashboard.py`, puis lancez `python build_dashboard.py` : le secret est injecté dans `const DIRECTLINE_SECRET` sans jamais apparaître dans un fichier versionné ;
   - ou directement dans le HTML généré, à la place de `<COLLER ICI LE SECRET 1>`.
3. Variante sans régénérer la page : panneau de chat → **Changer l'agent** → champ « Secret Direct Line ». Le secret est alors conservé dans ce navigateur uniquement.

**Connexion :**
- `WebChat.createDirectLine({ secret })` sur le domaine par défaut (directline.botframework.com) ;
- en cas d'échec (statut 3, 4 ou 5, ou délai de 20 s dépassé), nouvel essai sur `https://europe.directline.botframework.com/v3/directline` ;
- si ce second essai échoue aussi, repli sur l'iframe `COPILOT_URL` (agent `cr8ee_baliseiav2_RgZI7Z`), sans bandeau visible ; l'information est écrite en `console.info`.

Une fois la conversation en ligne, la page envoie l'événement `startConversation` (`locale: "fr-FR"`), qui déclenche le message d'accueil de l'agent.

**Mise en page :**
- colonne centrée de 860 px au maximum, avec des marges de 24 px ;
- réponses de l'agent sans bulle, sur toute la largeur ;
- questions de l'utilisateur dans une bulle #eef3f8 à droite ;
- police Segoe UI 15 px ;
- tableaux Markdown avec défilement horizontal, identifiants jamais coupés ;
- zone de saisie arrondie, sans bouton de pièce jointe ;
- un seul en-tête « BaliseIA – En ligne ».

**Comportement :**
- l'indicateur « BaliseIA analyse les données… » (trois points) reste affiché jusqu'au message de l'agent ; au bout de 90 s, il affiche un message d'excuse ;
- les questions suggérées et les boutons « Demander… » envoient directement la question ;
- la page Assistant et le panneau latéral partagent une seule conversation.

En mode iframe, le bandeau interne de Copilot Studio (48 px) est masqué par `--copilot-header`.
