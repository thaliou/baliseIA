# -*- coding: utf-8 -*-
"""
BaliseIA – Génération de l'outil BaliseIA_dashboard_G4.html

Injecte data.json dans un gabarit HTML (const DATA = …). Une seule page HTML,
navigation par onglets gérée en JavaScript (#resume, #recommandations,
#analyses, #equipements, #qualite, #assistant). Graphiques et icônes en SVG
générés en JavaScript vanilla.

- Indicateurs de pilotage (cartes, graphiques, anomalies) : recalculés dans le
  navigateur avec les règles de prepare_data.py.
- Classement, score, MTTR, cause principale par équipement : valeurs FIGÉES de
  la Base BaliseIA (section 3), lues dans data.json, jamais recalculées.
- Recommandations : Base BaliseIA (section 11), avec circuit de validation
  humaine conservé dans le localStorage du navigateur.

Chat : Bot Framework Web Chat relié à Copilot Studio par un secret Direct Line
(DIRECTLINE_SECRET, lu dans directline_secret.txt – fichier ignoré par git) ;
domaine par défaut puis domaine Europe ; repli sur l'iframe COPILOT_URL si le
secret est absent ou si la connexion échoue.

Usage : python build_dashboard.py            -> BaliseIA_dashboard_G4.html (avec le secret, usage local)
        python build_dashboard.py --partage  -> BaliseIA_dashboard_G4_partage.html (SANS secret, à partager)
(après python prepare_data.py)
"""
import base64
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DATA = ICI / "data.json"
SORTIE = ICI / "BaliseIA_dashboard_G4.html"
SORTIE_PARTAGE = ICI / "BaliseIA_dashboard_G4_partage.html"   # version sans secret, à diffuser
LOGO = ICI / "assets" / "logo_asecna.png"
# Secret Direct Line : jamais écrit dans ce script versionné. Il est lu dans directline_secret.txt
# (fichier ignoré par git) s'il existe ; sinon la page contient le texte à remplacer.
SECRET = ICI / "directline_secret.txt"
SECRET_A_COLLER = "<COLLER ICI LE SECRET 1>"

GABARIT = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BaliseIA – Maintenance du balisage</title>
<style>
:root{
 --marine:#0d2f55;--bleu:#0b4f8a;--bleu-fonce:#0d2f55;--bleu-pale:#e6eef7;
 --attention:#e07b2a;--attention-pale:#fdf1e6;--critique:#c0392b;--critique-pale:#fbeceb;
 --valide:#2e8b57;--valide-pale:#e8f4ed;--gris:#6b7785;--gris-clair:#9aa5b1;--gris-pale:#eef1f4;
 --fond:#f2f5f8;--carte:#fff;--texte:#1c2733;--trait:#dfe5eb;--menu:220px;--hb:68px;
 --copilot-header:48px;   /* hauteur du bandeau interne de l'iframe Copilot Studio (mesurée : 48 px) */
}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",Tahoma,Arial,sans-serif;color:var(--texte);font-size:14px;line-height:1.45;
 background:linear-gradient(to right,var(--marine) var(--menu),var(--fond) var(--menu))}
a{color:var(--bleu)}
button{font-family:inherit}
.ic{width:18px;height:18px;flex:none;vertical-align:middle}
/* ---------- Menu latéral ---------- */
.menu{position:fixed;top:0;left:0;height:100vh;width:var(--menu);background:var(--marine);color:#fff;display:flex;flex-direction:column;padding:18px 14px;z-index:20;overflow-y:auto}
.encart{display:flex;align-items:center;gap:8px;padding:2px 4px 10px;border-bottom:1px solid rgba(255,255,255,.15)}
.encart .logo{width:34px;height:34px;flex:none;border-radius:50%;background:#fff;padding:1px}
.encart b{font-size:13px;font-weight:600;color:#fff;letter-spacing:.3px}
.menu .groupe{margin:20px 0 6px 10px;font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:#8ea7c2}
.menu a{display:flex;align-items:center;gap:10px;color:#d5e1ee;text-decoration:none;padding:8px 10px;border-radius:7px;font-size:13.5px;border-left:3px solid transparent}
.menu a:hover{background:rgba(255,255,255,.07);color:#fff}
.menu a.actif{background:rgba(255,255,255,.12);color:#fff;font-weight:600;border-left-color:#fff}
.menu .pied{margin-top:auto;font-size:11.5px;line-height:1.5;color:#9fb4ca;border-top:1px solid rgba(255,255,255,.15);padding-top:12px}
/* ---------- Bandeau ---------- */
.page{margin-left:var(--menu);min-height:100vh;display:flex;flex-direction:column;background:var(--fond)}
.bandeau{display:flex;align-items:center;gap:20px;flex-wrap:wrap;background:#fff;padding:12px 24px;border-bottom:1px solid var(--trait);min-height:68px}
.bandeau .titres{flex:1;min-width:280px}
.bandeau .titres b{display:block;font-size:16px;color:var(--marine)}
.bandeau .titres small{color:var(--gris);font-size:12.5px}
.segments{display:inline-flex;border:1px solid var(--trait);border-radius:8px;overflow:hidden;background:#fff}
.segments button{border:0;background:#fff;color:var(--texte);padding:7px 14px;font-size:13px;cursor:pointer;border-right:1px solid var(--trait)}
.segments button:last-child{border-right:0}
.segments button:hover{background:var(--gris-pale)}
.segments button[aria-pressed="true"]{background:var(--bleu);color:#fff;font-weight:600}
.equipe{font-weight:600;color:var(--bleu);font-size:13px}
/* ---------- Pages ---------- */
main{flex:1;padding:22px 24px 90px}
.vue{display:none;flex-direction:column;gap:18px}
.vue.visible{display:flex}
.vue>header h1{margin:0;font-size:22px;font-weight:600;color:var(--marine)}
.vue>header p{margin:4px 0 0;color:var(--gris);font-size:13px}
.carte{background:var(--carte);border-radius:12px;padding:16px 18px;box-shadow:0 1px 2px rgba(13,47,85,.06),0 0 0 1px rgba(13,47,85,.04);min-width:0}
.carte>h2,.titre-carte{margin:0 0 12px;font-size:15px;font-weight:600;color:var(--marine);display:flex;align-items:center;gap:8px}
.titre-carte .droite,.carte>h2 .droite{margin-left:auto;display:flex;align-items:center;gap:10px;font-size:12.5px;font-weight:600}
.lien{color:var(--bleu);text-decoration:none;font-weight:600;font-size:12.5px;display:inline-flex;align-items:center;gap:4px}
.lien:hover{text-decoration:underline}
.note{margin-top:6px;font-size:12px;color:var(--gris)}
/* Source : icône (i) avec infobulle */
.src{position:relative;display:inline-flex;color:var(--gris-clair);cursor:help;outline:none}
.src:hover,.src:focus{color:var(--bleu)}
.src .ic{width:16px;height:16px}
.src::after{content:attr(data-tip);position:absolute;right:-6px;top:calc(100% + 8px);width:max-content;max-width:300px;background:var(--marine);color:#fff;font-size:12px;font-weight:400;line-height:1.4;padding:7px 10px;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.18);opacity:0;pointer-events:none;transform:translateY(-3px);transition:.12s;z-index:30;white-space:normal;text-align:left}
.src:hover::after,.src:focus::after{opacity:1;transform:none}
.g2{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:18px}
.g2e{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
/* Indicateurs */
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px}
.kpi{display:flex;gap:12px;align-items:center;padding:14px 16px}
.kpi .pic{flex:none;width:42px;height:42px;border-radius:50%;display:grid;place-items:center;background:var(--bleu-pale);color:var(--bleu)}
.kpi .pic .ic{width:20px;height:20px}
.kpi .val{font-size:28px;font-weight:600;color:var(--marine);line-height:1.1;white-space:nowrap}
.kpi .lib{font-size:12.5px;color:var(--gris)}
.kpi.critique .pic{background:var(--critique-pale);color:var(--critique)}
.kpi.critique .val{color:var(--critique)}
/* À retenir */
.retenir{display:flex;gap:16px;align-items:flex-start;border-left:4px solid var(--bleu)}
.retenir>.pic{flex:none;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;background:var(--bleu-pale);color:var(--bleu)}
.retenir ol{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px;font-size:14px}
.retenir ol li::marker{color:var(--bleu);font-weight:600}
.retenir .titre-carte{margin-bottom:8px}
.ref{font-family:Consolas,"Cascadia Mono",monospace;font-size:.92em;white-space:nowrap;color:var(--marine);background:var(--gris-pale);border-radius:4px;padding:0 4px}
/* Pastilles de statut */
.statut{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap;border:1px solid transparent}
.statut.attention{background:var(--attention-pale);color:#a5520f;border-color:#f3d2b3}
.statut.valide{background:var(--valide-pale);color:var(--valide);border-color:#bfe0cc}
.statut.rejete{background:var(--gris-pale);color:var(--gris);border-color:var(--trait)}
.statut.critique{background:var(--critique-pale);color:var(--critique);border-color:#efc4bf}
.statut.neutre{background:#fff;color:var(--gris);border-color:var(--trait)}
.statut.info{background:var(--bleu-pale);color:var(--bleu);border-color:#cddcec}
/* Tableaux */
.tab{overflow:auto;border-radius:8px;border:1px solid var(--trait)}
table.dt{width:100%;border-collapse:collapse;font-size:13px}
table.dt th{position:sticky;top:0;background:var(--marine);color:#fff;text-align:left;padding:8px 10px;font-weight:600;white-space:nowrap;z-index:1}
table.dt th.num,table.dt td.num{text-align:right}
table.dt td{padding:8px 10px;border-bottom:1px solid var(--trait);vertical-align:top}
table.dt tr:last-child td{border-bottom:0}
table.dt tr:nth-child(even) td{background:#f9fbfc}
table.dt .nowrap{white-space:nowrap}
table.dt tr.clic{cursor:pointer}
table.dt tr.clic:hover td{background:var(--bleu-pale)}
table.dt tr.sel td{background:var(--bleu-pale)}
.score{font-weight:600;color:var(--bleu)}
.secondaire{color:var(--gris)}
/* Boutons */
.btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--trait);background:#fff;color:var(--texte);border-radius:7px;padding:6px 12px;font-size:13px;cursor:pointer;white-space:nowrap}
.btn:hover{background:var(--gris-pale)}
.btn .ic{width:16px;height:16px}
.btn.prim{background:var(--bleu);border-color:var(--bleu);color:#fff}
.btn.prim:hover{background:var(--marine)}
.btn.ok{background:var(--valide);border-color:var(--valide);color:#fff}
.btn.ok:hover{filter:brightness(.92)}
.btn.petit{padding:4px 10px;font-size:12.5px}
/* Alertes qualité */
.alertes{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.alertes li{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--gris-pale);font-size:13.5px}
.alertes li:last-child{border-bottom:0}
.alertes li b{margin-left:auto;font-size:15px;color:var(--marine)}
.alertes .ic{color:var(--gris-clair)}
.alertes li.attention .ic{color:var(--attention)}
.alertes li.critique .ic{color:var(--critique)}
/* Recommandations */
.avert{display:flex;gap:12px;align-items:center;background:var(--bleu-pale);border:1px solid #cddcec;color:var(--marine);border-radius:10px;padding:12px 16px;font-size:13.5px}
.avert .ic{color:var(--bleu);width:20px;height:20px}
.recs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.rec{display:flex;flex-direction:column;gap:10px;border-top:3px solid var(--attention);scroll-margin-top:20px;transition:box-shadow .3s}
.rec.s-valide{border-top-color:var(--valide)}
.rec.s-rejete{border-top-color:var(--gris-clair)}
.rec.flash{box-shadow:0 0 0 3px rgba(11,79,138,.35)}
.rec header{display:flex;align-items:flex-start;gap:10px}
.rec header .ident{flex:1;min-width:0}
.rec header .ident b{display:block;font-size:15px;color:var(--marine)}
.rec header .ident small{color:var(--gris);font-size:12.5px}
.rec-id{font-family:Consolas,monospace;font-size:12px;color:var(--bleu);background:var(--bleu-pale);border-radius:4px;padding:1px 6px;white-space:nowrap}
.rec dl{margin:0;display:grid;grid-template-columns:120px 1fr;gap:6px 12px;font-size:13.5px}
.rec dt{color:var(--gris);font-weight:600;font-size:12.5px;padding-top:1px}
.rec dd{margin:0}
.rec .trace{font-size:12.5px;color:var(--gris);background:var(--gris-pale);border-radius:6px;padding:6px 10px}
.rec .trace.valide{background:var(--valide-pale);color:#23704a}
.rec form{display:none;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr);gap:8px 12px;border-top:1px solid var(--gris-pale);padding-top:10px}
.rec.form-ouvert form{display:grid}
.rec.form-ouvert .actions-carte [data-action=decider]{display:none}
.rec form input,.rec form textarea{width:100%;box-sizing:border-box}
.rec .actions-carte{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.rec label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--gris);font-weight:600}
.rec input,.rec textarea{font:inherit;font-size:13px;border:1px solid var(--trait);border-radius:6px;padding:6px 8px;color:var(--texte);resize:vertical}
.rec input.erreur{border-color:var(--critique);box-shadow:0 0 0 2px var(--critique-pale)}
.rec .actions{grid-column:1/-1;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.rec .msg{font-size:12px;color:var(--critique)}
.req{color:var(--critique)}
.journal-actions{display:flex;gap:8px}
/* Qualité */
.chips{display:flex;flex-wrap:wrap;gap:10px}
.chip{background:#fff;border:1px solid var(--trait);border-radius:10px;padding:10px 14px;font-size:13px;color:var(--gris);display:flex;align-items:baseline;gap:8px}
.chip b{font-size:22px;font-weight:600;color:var(--marine)}
.chip.attention b{color:var(--attention)}
.chip.critique b{color:var(--critique)}
/* Graphiques */
svg.graph{display:block;width:100%;height:auto;max-height:300px}
svg text{font-family:"Segoe UI",Tahoma,Arial,sans-serif}
.vide{color:var(--gris);font-style:italic;padding:20px;text-align:center}
footer{text-align:center;font-style:italic;color:var(--gris);font-size:12.5px;padding:10px 24px 16px}
/* ---------- Fiche équipement (panneau latéral) ---------- */
.voile{position:fixed;inset:0;background:rgba(13,47,85,.28);z-index:45;opacity:0;pointer-events:none;transition:opacity .2s}
.voile.ouvert{opacity:1;pointer-events:auto}
.volet{position:fixed;top:0;right:0;bottom:0;width:min(560px,100vw);background:#fff;z-index:46;transform:translateX(105%);transition:transform .25s ease;display:flex;flex-direction:column;box-shadow:-8px 0 30px rgba(13,47,85,.18)}
.volet.ouvert{transform:none}
.volet>header{display:flex;align-items:flex-start;gap:12px;padding:18px 20px;border-bottom:1px solid var(--trait)}
.volet>header h2{margin:0;font-size:20px;font-weight:600;color:var(--marine)}
.volet>header small{display:block;color:var(--gris);font-size:13px}
.volet .corps{flex:1;overflow:auto;padding:16px 20px 24px;display:flex;flex-direction:column;gap:18px}
.volet h3{margin:0 0 8px;font-size:14px;font-weight:600;color:var(--marine);display:flex;align-items:center;gap:8px}
.icone-btn{border:0;background:var(--gris-pale);color:var(--marine);border-radius:8px;width:34px;height:34px;display:grid;place-items:center;cursor:pointer;flex:none}
.icone-btn:hover{background:var(--trait)}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.stat{background:var(--gris-pale);border-radius:8px;padding:8px 10px}
.stat span{display:block;font-size:11.5px;color:var(--gris)}
.stat b{font-size:15px;font-weight:600;color:var(--marine)}
.stat.critique b{color:var(--critique)}
.lie{border:1px solid var(--trait);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:8px;font-size:13.5px}
.lie .ligne{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
/* ---------- Chat ---------- */
.chat{position:fixed;z-index:50;background:#fff;display:flex;flex-direction:column;overflow:hidden;box-shadow:-8px 0 30px rgba(13,47,85,.18)}
.chat.tiroir{top:0;right:0;bottom:0;width:min(520px,100vw);transform:translateX(105%);transition:transform .25s ease}
.chat.tiroir.ouvert{transform:none}
/* Page Assistant : panneau centré dans la zone de contenu, 920 px max, sous le bandeau, au-dessus du pied de page */
.chat.pleine{top:calc(var(--hb) + 16px);left:calc(var(--menu) + 24px);right:24px;bottom:auto;margin:0 auto;width:min(920px,calc(100vw - var(--menu) - 48px));
 height:min(calc(100vh - 160px),calc(100vh - var(--hb) - 72px));border-radius:12px;box-shadow:0 1px 2px rgba(13,47,85,.06),0 0 0 1px rgba(13,47,85,.06)}
.chat-tete{background:var(--marine);color:#fff;padding:10px 12px 10px 16px;display:flex;align-items:center;gap:8px;flex:none}
.chat-tete b{flex:1;font-size:14.5px;font-weight:600;display:flex;align-items:center;gap:8px}
.chat-tete b::before{content:"";width:8px;height:8px;border-radius:50%;background:#9aa5b1;box-shadow:0 0 0 3px rgba(154,165,177,.25)}
/* Indicateur de connexion : vert = Web Chat connecté, orange = repli iframe, gris = connexion en cours */
.chat-tete b.etat-en-ligne::before{background:#4cc38a;box-shadow:0 0 0 3px rgba(76,195,138,.25)}
.chat-tete b.etat-iframe::before{background:var(--attention);box-shadow:0 0 0 3px rgba(224,123,42,.3)}
.chat-tete b.etat-connexion::before{background:#9aa5b1;animation:pulse 1.2s infinite ease-in-out}
@keyframes pulse{50%{opacity:.35}}
.chat-tete button{border:0;border-radius:6px;padding:6px 8px;cursor:pointer;background:rgba(255,255,255,.12);color:#fff;display:inline-flex;align-items:center;gap:6px;font-size:12.5px}
.chat-tete button:hover{background:rgba(255,255,255,.2)}
.chat-tete .ic{width:16px;height:16px}
.chat.pleine #btnFermer{display:none}
.mode{flex:none;display:none;background:var(--attention-pale);color:#8a4410;font-size:12px;padding:6px 16px;border-bottom:1px solid #f3d2b3}
.mode.visible{display:block}
.config{display:none;flex:none;padding:10px 14px;background:#f6f8fa;border-bottom:1px solid var(--trait);font-size:12px}
.config.ouvert{display:block}
.config label{display:block;margin-top:6px;color:var(--gris);font-weight:600}
.config input,.config textarea{width:100%;font:12px Consolas,monospace;border:1px solid var(--trait);border-radius:6px;padding:6px;margin-top:3px}
.config textarea{height:56px;resize:vertical}
.config .actions{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
#webchat{flex:1;min-height:0;position:relative;background:#fff;display:flex;flex-direction:column}
#webchat>div{height:100%}
/* Mode iframe : le bandeau interne de Copilot Studio (« BaliseIA v2 ») est masqué en décalant l'iframe
   vers le haut dans un conteneur qui rogne ; seul notre en-tête « BaliseIA – En ligne » reste visible */
.chat-frame{position:relative;overflow:hidden;flex:1;min-height:0}
.chat-frame iframe{position:absolute;top:calc(-1 * var(--copilot-header));left:0;width:100%;height:calc(100% + var(--copilot-header));border:0}
.attente{flex:none;display:none;align-items:center;gap:8px;padding:7px 16px;font-size:12.5px;color:var(--bleu);background:var(--bleu-pale);border-top:1px solid #cddcec}
.attente.visible{display:flex}
.attente.lent{color:#8a4410;background:var(--attention-pale)}
.points{display:inline-flex;gap:3px}
.points i{width:6px;height:6px;border-radius:50%;background:var(--bleu);animation:rebond 1.2s infinite ease-in-out}
.points i:nth-child(2){animation-delay:.15s}.points i:nth-child(3){animation-delay:.3s}
@keyframes rebond{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
.questions{flex:none;border-top:1px solid var(--trait);padding:9px 14px 10px;max-height:34%;overflow:auto}
.questions h4{margin:0 0 6px;font-size:12px;color:var(--gris);font-weight:600}
.questions .liste{display:flex;flex-wrap:wrap;gap:6px}
.questions button{text-align:left;font-size:12.5px;background:#fff;color:var(--bleu);border:1px solid #cddcec;border-radius:16px;padding:4px 11px;cursor:pointer}
.questions button:hover{background:var(--bleu-pale)}
.toast{min-height:14px;font-size:11.5px;color:var(--gris);margin-top:4px}
.a-coller{flex:none;background:var(--attention-pale);border-bottom:1px solid #f3d2b3;padding:10px 14px;font-size:12.5px;color:#5a2d08;display:flex;flex-direction:column;gap:6px}
.a-coller[hidden]{display:none}
.a-coller-tete{display:flex;align-items:flex-start;gap:8px}
.a-coller-tete b{flex:1}
.a-coller .icone-btn{width:26px;height:26px;background:rgba(255,255,255,.6)}
.a-coller .icone-btn .ic{width:14px;height:14px}
.a-coller-texte{background:#fff;border:1px dashed #e0b48a;border-radius:6px;padding:7px 9px;font-size:13px;color:var(--texte);user-select:all}
.a-coller-pied{display:flex;align-items:center;gap:10px;font-size:11.5px;color:#8a4410}
/* Bouton flottant : icône ronde de 56 px, libellé au survol */
.fab{position:fixed;right:24px;bottom:24px;z-index:40;width:56px;height:56px;border:0;border-radius:50%;background:var(--bleu);color:#fff;display:grid;place-items:center;box-shadow:0 4px 14px rgba(11,79,138,.35);cursor:pointer}
.fab:hover,.fab:focus-visible{background:var(--marine)}
.fab .ic{width:24px;height:24px}
.fab::after{content:attr(aria-label);position:absolute;right:66px;top:50%;transform:translateY(-50%) translateX(6px);background:var(--marine);color:#fff;font-size:13px;font-weight:600;padding:6px 12px;border-radius:6px;white-space:nowrap;opacity:0;pointer-events:none;transition:.15s}
.fab:hover::after,.fab:focus-visible::after{opacity:1;transform:translateY(-50%)}
.fab[hidden]{display:none}
.place-assistant{height:calc(100vh - 200px)}
.titre-masque{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
body.sur-assistant footer{position:fixed;left:var(--menu);right:0;bottom:0;padding:14px 24px}
/* Web Chat – mise en page « ChatGPT » : colonne centrée de 860 px max, marges de 24 px,
   réponses de l'agent sans bulle sur toute la largeur, questions en bulle claire à droite, Segoe UI 15 px */
#webchat .webchat__basic-transcript__transcript{width:100%;max-width:860px;margin:0 auto !important;padding:16px 24px !important;box-sizing:border-box}
#webchat .webchat__basic-transcript__activity{padding-left:0 !important;padding-right:0 !important}
#webchat .webchat__stacked-layout{margin-left:0 !important;margin-right:0 !important}
#webchat .webchat__bubble__nub-pad{display:none !important}
#webchat .webchat__stacked-layout:not(.webchat__stacked-layout--from-user) .webchat__text-content{padding:0 !important}
#webchat .webchat__stacked-layout__status,#webchat .webchat__stacked-layout__alignment-pad{margin-left:0 !important}
/* L'indicateur de Web Chat est remplacé par « BaliseIA analyse les données… » */
#webchat [class*="typing-indicator"]{display:none !important}
#webchat .webchat__stacked-layout__avatar-gutter,#webchat .webchat__stacked-layout__nub-pad{display:none !important}
#webchat .webchat__bubble__content{font-size:15px;line-height:1.6}
#webchat .webchat__stacked-layout:not(.webchat__stacked-layout--from-user) .webchat__stacked-layout__content{flex:1 1 auto;max-width:100% !important}
#webchat .webchat__stacked-layout:not(.webchat__stacked-layout--from-user) .webchat__bubble{width:100%;max-width:none}
#webchat .webchat__stacked-layout:not(.webchat__stacked-layout--from-user) .webchat__bubble__content{background:transparent !important;border:0 !important;padding:2px 0 !important}
#webchat .webchat__stacked-layout--from-user .webchat__stacked-layout__content{max-width:80% !important}
#webchat .webchat__stacked-layout--from-user .webchat__bubble__content{padding:8px 14px !important}
/* Zone de saisie arrondie, centrée en bas */
#webchat .webchat__send-box{max-width:812px;width:calc(100% - 48px);margin:0 auto 14px !important;background:transparent !important}
#webchat .webchat__send-box__main{border:1px solid #d5dde6 !important;border-radius:24px;background:#fff;padding:2px 6px 2px 16px;box-shadow:0 1px 6px rgba(13,47,85,.08)}
#webchat .webchat__send-box-text-box__input,#webchat .webchat__send-box-text-box__text-area{font-size:15px}
#webchat .webchat__upload-button{display:none !important}
/* Markdown de l'agent : titres, listes, tableaux lisibles */
#webchat .webchat__render-markdown{overflow-x:auto;line-height:1.6}
#webchat .webchat__render-markdown p{margin:6px 0 8px}
#webchat .webchat__render-markdown h1,#webchat .webchat__render-markdown h2,#webchat .webchat__render-markdown h3,#webchat .webchat__render-markdown h4{margin:16px 0 6px;font-size:16px;color:var(--marine)}
#webchat .webchat__render-markdown ul,#webchat .webchat__render-markdown ol{margin:6px 0 10px;padding-left:22px}
#webchat .webchat__render-markdown li{margin:4px 0}
#webchat table{border-collapse:collapse;font-size:13.5px;display:block;overflow-x:auto;max-width:100%;margin:10px 0}
#webchat th,#webchat td{border:1px solid #e1e8f0;padding:6px 10px;text-align:left;white-space:nowrap;vertical-align:top}
#webchat th{background:#eaf2fb;color:var(--marine);font-weight:600}
#webchat tr:nth-child(even) td{background:#f9fbfc}#webchat .id-nowrap{white-space:nowrap}
/* ---------- Rapports ---------- */
.parametres{display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap}
.parametres label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:600;color:var(--gris)}
.parametres select{font:inherit;font-size:13.5px;padding:6px 10px;border:1px solid var(--trait);border-radius:7px;color:var(--texte);min-width:200px;background:#fff}
.parametres .droite{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.btn:disabled{opacity:.45;cursor:not-allowed}
.rapport-zone{overflow-x:auto;padding:4px 0 8px}
.rapport{display:flex;flex-direction:column;align-items:center;gap:22px;min-width:min-content}
.feuille{width:210mm;min-height:297mm;background:#fff;padding:16mm 15mm 22mm;box-shadow:0 2px 10px rgba(13,47,85,.12);position:relative;font-size:10.5pt;line-height:1.45;color:#1c2733}
.feuille h2{font-size:15pt;font-weight:600;color:var(--marine);margin:0 0 4mm;padding-bottom:2mm;border-bottom:2px solid var(--bleu)}
.feuille h3{font-size:11.5pt;font-weight:600;color:var(--marine);margin:6mm 0 2mm}
.feuille p{margin:0 0 2.5mm}
.feuille .src-r{font-size:8.5pt;color:var(--gris);margin-top:3mm}
.pied-feuille{position:absolute;left:15mm;right:15mm;bottom:9mm;border-top:1px solid var(--trait);padding-top:2mm;font-size:8pt;color:var(--gris)}
.garde{display:flex;flex-direction:column;justify-content:center;text-align:left}
.garde .logo-r{width:26mm;height:26mm;margin-bottom:10mm}
.garde .surtitre{font-size:11pt;color:var(--bleu);font-weight:600;letter-spacing:.3px;text-transform:uppercase}
.garde h1{font-size:26pt;line-height:1.2;color:var(--marine);margin:4mm 0 6mm;font-weight:600}
.garde .meta{font-size:11.5pt;color:#3b4856;border-left:3px solid var(--bleu);padding-left:5mm;display:flex;flex-direction:column;gap:2mm}
.garde .demo{margin-top:14mm;display:inline-block;border:1px solid #f3d2b3;background:var(--attention-pale);color:#8a4410;border-radius:6px;padding:3mm 5mm;font-size:10pt;font-weight:600}
.constats{margin:0;padding-left:6mm;display:flex;flex-direction:column;gap:3mm;font-size:11pt}
.constats li::marker{color:var(--bleu);font-weight:600}
table.rt{width:100%;border-collapse:collapse;font-size:9.5pt;margin:2mm 0 3mm}
table.rt th{background:var(--bleu-pale);color:var(--marine);font-weight:600;text-align:left;padding:2mm 2.5mm;border-bottom:1.5px solid var(--bleu)}
table.rt td{padding:1.6mm 2.5mm;border-bottom:1px solid var(--trait);vertical-align:top}
table.rt .num{text-align:right;white-space:nowrap}
table.rt .nowrap{white-space:nowrap}
.delta{font-weight:600;white-space:nowrap}
.delta.hausse{color:#a5520f}
.delta.baisse{color:var(--gris)}
.deux{display:grid;grid-template-columns:1fr 1fr;gap:6mm}
.rec-r{border:1px solid var(--trait);border-left:3px solid var(--attention);border-radius:4px;padding:2.5mm 3.5mm;margin-bottom:3mm;break-inside:avoid}
.rec-r.s-valide{border-left-color:var(--valide)}
.rec-r.s-rejete{border-left-color:var(--gris-clair)}
.rec-r header{display:flex;gap:3mm;align-items:baseline;flex-wrap:wrap;margin-bottom:1mm}
.rec-r header b{color:var(--marine)}
.rec-r .st{margin-left:auto;font-size:9pt;font-weight:600}
.rec-r .st.attention{color:#a5520f}.rec-r .st.valide{color:var(--valide)}.rec-r .st.rejete{color:var(--gris)}
.rec-r p{font-size:9.5pt;margin:0 0 1mm}
.methode li{margin-bottom:1.5mm}
.sect+.sect{margin-top:8mm}
.barre-cel{display:inline-block;width:20mm;height:2.8mm;background:#e7ecf1;border-radius:1px;vertical-align:middle;margin-right:2mm;overflow:hidden}
.barre-cel i{display:block;height:100%}
.liste-ids{font-family:Consolas,monospace;font-size:8.5pt;line-height:1.5}
.deux .graphe svg.graph{max-height:42mm}
.note-impr{flex-basis:100%;font-size:12px;color:var(--gris);display:flex;align-items:center;gap:6px}
.note-impr .ic{width:15px;height:15px;color:var(--bleu)}
@media print{
 body[data-vue="rapports"]{background:#fff !important}
 body[data-vue="rapports"] .menu,body[data-vue="rapports"] .bandeau,body[data-vue="rapports"] .chat,body[data-vue="rapports"] .fab,
 body[data-vue="rapports"] .voile,body[data-vue="rapports"] .volet,body[data-vue="rapports"] .page>footer,
 body[data-vue="rapports"] #v-rapports>header,body[data-vue="rapports"] #v-rapports>.parametres{display:none !important}
 body[data-vue="rapports"] .page{margin-left:0;background:#fff;min-height:0;display:block}
 body[data-vue="rapports"] main{padding:0}
 body[data-vue="rapports"] .rapport-zone{overflow:visible;padding:0}
 body[data-vue="rapports"] .rapport{display:block}
 body[data-vue="rapports"] .feuille{width:auto;min-height:0;box-shadow:none;padding:0;margin:0;break-before:page}
 body[data-vue="rapports"] .feuille:first-child{break-before:auto}
 body[data-vue="rapports"] .garde{min-height:250mm}
 body[data-vue="rapports"] .pied-feuille{display:none}
 body[data-vue="rapports"] table.rt thead{display:table-header-group}
 body[data-vue="rapports"] table.rt tr{break-inside:avoid}
 body[data-vue="rapports"] .feuille h2,body[data-vue="rapports"] .feuille h3{break-after:avoid}
 body[data-vue="rapports"] .rec-r,body[data-vue="rapports"] table.rt.court,body[data-vue="rapports"] .graphe,
 body[data-vue="rapports"] .deux,body[data-vue="rapports"] .constats{break-inside:avoid}
 body[data-vue="rapports"] .feuille{font-size:10pt}
 body[data-vue="rapports"] .sect+.sect{margin-top:4mm}
 body[data-vue="rapports"] svg.graph{max-height:40mm}
 body[data-vue="rapports"] .deux .graphe svg.graph{max-height:30mm}
 body[data-vue="rapports"] .feuille h2{font-size:13pt;margin-bottom:2.5mm;padding-bottom:1.2mm}
 body[data-vue="rapports"] .feuille h3{margin:3mm 0 1.5mm;font-size:10.5pt}
 body[data-vue="rapports"] .constats{font-size:9.5pt;gap:1.2mm;line-height:1.35}
 body[data-vue="rapports"] table.rt{font-size:9pt;margin:1mm 0 2mm}
 body[data-vue="rapports"] table.rt td,body[data-vue="rapports"] table.rt th{padding:.8mm 2.2mm;line-height:1.3}
 body[data-vue="rapports"] .src-r{margin-top:1.5mm;font-size:8pt}
 body[data-vue="rapports"] #r-anomalies table.rt{font-size:8.5pt}
 body[data-vue="rapports"] #r-anomalies table.rt td,body[data-vue="rapports"] #r-anomalies table.rt th{padding:1.1mm 1.8mm;line-height:1.3}
 body[data-vue="rapports"] .liste-ids{font-family:inherit;font-size:8.5pt;line-height:1.35}
 body[data-vue="rapports"] .rec-r{padding:1.8mm 3mm;margin-bottom:2mm}
 body[data-vue="rapports"] .rec-r p{font-size:8.6pt;line-height:1.33;margin:0 0 .6mm}
 body[data-vue="rapports"] .rec-r .ref{font-size:8pt;padding:0 2px}
 body[data-vue="rapports"] .methode li{font-size:9pt;margin-bottom:1mm}
 body[data-vue="rapports"] .deux.methode-bloc{break-inside:auto}
 body[data-vue="rapports"] *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
@media (max-width:1300px){
 .kpis{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
 .g2,.g2e,.recs{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:760px){
 body{background:var(--fond)}
 .menu{position:static;width:auto;height:auto}
 .page{margin-left:0}
 main{padding:14px 12px 90px}
 .chat.pleine{left:8px;right:8px;top:8px;width:auto;height:calc(100vh - 60px)}
 body.sur-assistant footer{left:0}
 .rec form{grid-template-columns:1fr}
 .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
}
</style>
</head>
<body>
<aside class="menu">
 <div class="encart">__LOGO__<b>ATSA-ASECNA</b></div>
 <nav id="nav">
  <div class="groupe">Pilotage</div>
  <a href="#resume" data-vue="resume"><i data-ic="jauge"></i>Accueil</a>
  <a href="#recommandations" data-vue="recommandations"><i data-ic="valider"></i>Recommandations</a>
  <a href="#rapports" data-vue="rapports"><i data-ic="rapport"></i>Rapports</a>
  <div class="groupe">Analyse</div>
  <a href="#analyses" data-vue="analyses"><i data-ic="barres"></i>Analyses</a>
  <a href="#equipements" data-vue="equipements"><i data-ic="balise"></i>Équipements</a>
  <a href="#qualite" data-vue="qualite"><i data-ic="bouclier"></i>Qualité des données</a>
  <div class="groupe">Assistant</div>
  <a href="#assistant" data-vue="assistant"><i data-ic="message"></i>BaliseIA</a>
 </nav>
 <div class="pied">Thématique 04 – Maintenance du balisage<br>Groupe G4 – UAM</div>
</aside>

<div class="page">
 <header class="bandeau">
  <div class="titres"><b>Assistant de maintenance du balisage</b><small id="contexte"></small></div>
  <div class="segments" id="filtre" role="group" aria-label="Filtrer par site">
   <button type="button" data-site="" aria-pressed="true">Tous</button>
   <button type="button" data-site="DAK-SIM" aria-pressed="false">Dakar</button>
   <button type="button" data-site="NIM-SIM" aria-pressed="false">Niamey</button>
   <button type="button" data-site="ABJ-SIM" aria-pressed="false">Abidjan</button>
  </div>
  <span class="equipe">Équipe G4 – UAM</span>
 </header>

 <main>
  <!-- ===================== Accueil (cockpit) ===================== -->
  <section class="vue" id="v-resume">
   <header><h1>Accueil</h1></header>
   <div class="carte retenir">
    <div class="pic"><i data-ic="ampoule"></i></div>
    <div style="flex:1;min-width:0">
     <div class="titre-carte">À retenir<span class="droite"><span data-src="2,3,6,8"></span></span></div>
     <ol id="retenir"></ol>
    </div>
   </div>
   <div>
    <div class="kpis" id="kpis"></div>
    <div class="note" style="display:flex;justify-content:flex-end"><span data-src="2"></span></div>
   </div>
   <div class="carte">
    <div class="titre-carte">Actions à valider cette semaine<span class="droite"><a class="lien" href="#recommandations">Toutes les recommandations <i data-ic="fleche"></i></a><span data-src="11"></span></span></div>
    <div class="tab"><table class="dt"><thead><tr><th>Équipement</th><th>Constat</th><th>Action proposée</th><th></th></tr></thead><tbody id="tActions"></tbody></table></div>
   </div>
   <div class="g2">
    <div class="carte"><div class="titre-carte">Pannes par mois<span class="droite"><a class="lien" href="#analyses">Analyses <i data-ic="fleche"></i></a><span data-src="7,12"></span></span></div><div id="gMiniMois"></div></div>
    <div class="carte"><div class="titre-carte">Alertes qualité<span class="droite"><a class="lien" href="#qualite">Détail <i data-ic="fleche"></i></a><span data-src="10"></span></span></div><ul class="alertes" id="lAlertes"></ul></div>
   </div>
  </section>

  <!-- ===================== Recommandations ===================== -->
  <section class="vue" id="v-recommandations">
   <header><h1>Recommandations</h1><p>Recommandations documentées de la Base BaliseIA, soumises à validation humaine.</p></header>
   <div class="avert"><i data-ic="info"></i><span><b>Aucune action n'est déclenchée automatiquement : la décision appartient à l'expert métier.</b> Chaque décision est horodatée et tracée dans le journal ci-dessous.</span></div>
   <div class="titre-carte" style="margin:4px 0 0">Recommandations par équipement <span id="nbRecEq" class="secondaire" style="font-weight:400"></span><span class="droite"><span data-src="11,3"></span></span></div>
   <div class="recs" id="recsEq"></div>
   <div class="titre-carte" style="margin:8px 0 0">Recommandations transverses<span class="droite"><span data-src="11"></span></span></div>
   <div class="recs" id="recsT"></div>
   <div class="carte" id="journal">
    <div class="titre-carte">Journal de validation <span id="nbJournal" class="secondaire" style="font-weight:400"></span>
     <span class="droite journal-actions">
      <button type="button" class="btn petit" id="btnExport"><i data-ic="telecharger"></i>Exporter le journal (CSV)</button>
      <button type="button" class="btn petit" id="btnReset"><i data-ic="reinit"></i>Réinitialiser la démo</button>
     </span></div>
    <div class="tab" style="max-height:360px"><table class="dt"><thead><tr><th>Date et heure</th><th>Validateur</th><th>Recommandation</th><th>Décision</th><th>N° OT</th><th>Commentaire</th></tr></thead><tbody id="tJournal"></tbody></table></div>
    <div class="note">Décisions conservées dans ce navigateur uniquement (stockage local).</div>
   </div>
  </section>

  <!-- ===================== Rapports ===================== -->
  <section class="vue" id="v-rapports">
   <header><h1>Rapports</h1><p>Rapport de maintenance imprimable, calculé avec les règles et les valeurs de la Base BaliseIA.</p></header>
   <div class="carte parametres">
    <label>Période<select id="rapPeriode"></select></label>
    <label>Site<select id="rapSite"><option value="">Tous</option><option value="DAK-SIM">Dakar</option><option value="NIM-SIM">Niamey</option><option value="ABJ-SIM">Abidjan</option></select></label>
    <button type="button" class="btn prim" id="btnGenerer">Générer le rapport</button>
    <span class="droite">
     <button type="button" class="btn" id="btnImprimer" disabled><i data-ic="imprimer"></i>Imprimer / Enregistrer en PDF</button>
     <button type="button" class="btn" id="btnCommenter"><i data-ic="message"></i>Demander à BaliseIA de commenter ce rapport</button>
    </span>
    <div class="note-impr"><i data-ic="info"></i>Dans la fenêtre d'impression, décochez « En-têtes et pieds de page » : le rapport a déjà son propre pied de page numéroté.</div>
   </div>
   <div class="rapport-zone"><div class="rapport" id="rapport"><div class="carte vide" style="width:100%">Choisissez une période et un site, puis cliquez sur « Générer le rapport ».</div></div></div>
  </section>

  <!-- ===================== Analyses ===================== -->
  <section class="vue" id="v-analyses">
   <header><h1>Analyses</h1></header>
   <div class="g2e">
    <div class="carte"><div class="titre-carte">Pannes par équipement (top 10)<span class="droite"><span data-src="3" data-plus="Égalités départagées par score de priorité."></span></span></div><div id="gEquip"></div></div>
    <div class="carte"><div class="titre-carte" id="titreSite">Pannes par site<span class="droite"><span data-src="6"></span></span></div><div id="gSite"></div></div>
    <div class="carte"><div class="titre-carte">Pannes par mois<span class="droite"><span data-src="7,12"></span></span></div><div id="gMois"></div></div>
    <div class="carte"><div class="titre-carte">Causes de panne (hors contrôles périodiques)<span class="droite"><span data-src="8"></span></span></div><div id="gCauses"></div></div>
    <div class="carte"><div class="titre-carte">Pièces remplacées<span class="droite"><span data-src="9" data-plus="« Aucune » n'est pas une pièce et n'est pas comptée."></span></span></div><div id="gPieces"></div></div>
   </div>
  </section>

  <!-- ===================== Équipements ===================== -->
  <section class="vue" id="v-equipements">
   <header><h1>Équipements</h1><p>Classement de priorité pour la maintenance préventive. Cliquez sur une ligne pour ouvrir la fiche.</p></header>
   <div class="carte">
    <div class="titre-carte" id="titreEquip">Classement<span class="droite"><span data-src="3" data-plus="Score, MTTR, durée et cause principale repris tels quels de la Base (valeurs figées)."></span></span></div>
    <div class="tab" style="max-height:660px"><table class="dt"><thead id="hEquip"></thead><tbody id="tEquip"></tbody></table></div>
   </div>
  </section>

  <!-- ===================== Qualité des données ===================== -->
  <section class="vue" id="v-qualite">
   <header><h1>Qualité des données</h1></header>
   <div class="chips" id="chipsQualite"></div>
   <div class="carte">
    <div class="titre-carte" id="titreQualite">Anomalies détectées<span class="droite"><span data-src="10,1"></span></span></div>
    <div class="tab" style="max-height:620px"><table class="dt"><thead><tr><th>Incident</th><th>Équipement</th><th>Site</th><th>Type</th><th>Détail</th><th>Traitement appliqué</th></tr></thead><tbody id="tQualite"></tbody></table></div>
   </div>
   <div class="carte" id="carteEcarts">
    <div class="titre-carte">Écarts et corrections de la Base<span class="droite"><span data-src="3,11" data-plus="L'outil utilise partout la Base corrigée : une seule valeur de score et de cause principale par équipement."></span></span></div>
    <div class="tab"><table class="dt"><thead><tr><th>Élément</th><th>Valeur</th><th>Base d'origine</th><th>Autre valeur</th><th>Traitement</th></tr></thead><tbody id="tEcarts"></tbody></table></div>
   </div>
  </section>

  <!-- ===================== Assistant ===================== -->
  <section class="vue" id="v-assistant"><h1 class="titre-masque">Assistant BaliseIA</h1><div class="place-assistant"></div></section>
 </main>
 <footer>Données fictives – ne pas utiliser pour la maintenance réelle. Toute recommandation doit être validée par un expert métier.</footer>
</div>

<!-- Fiche équipement (panneau latéral) -->
<div class="voile" id="voile"></div>
<aside class="volet" id="volet" role="dialog" aria-modal="true" aria-labelledby="ficheTitre"></aside>

<!-- Chat BaliseIA : instance unique, en tiroir ou en pleine page -->
<button type="button" class="fab" id="fab" aria-label="Demander à BaliseIA"><i data-ic="message"></i></button>
<aside class="chat tiroir" id="chat" aria-label="BaliseIA">
 <div class="chat-tete"><b id="etatChat" class="etat-connexion">BaliseIA – Connexion…</b>
  <button type="button" id="btnConfig" title="Changer l'agent"><i data-ic="reglages"></i>Changer l'agent</button>
  <button type="button" id="btnFermer" title="Fermer" aria-label="Fermer"><i data-ic="fermer"></i></button></div>
 <div class="config" id="config">
  <label>Secret Direct Line (chat personnalisé) – conservé dans ce navigateur uniquement
   <input id="champSecret" type="password" autocomplete="off" placeholder="Secret 1 du canal Direct Line de l'agent"></label>
  <label>URL ou code &lt;iframe&gt; (mode de repli)
   <textarea id="champIframe"></textarea></label>
  <div class="actions">
   <button type="button" class="btn petit prim" id="btnConnecter">Connecter</button>
   <button type="button" class="btn petit" id="btnOnglet"><i data-ic="externe"></i>Ouvrir dans un onglet</button>
   <button type="button" class="btn petit" id="btnDefaut">Agent par défaut</button>
  </div>
  <div class="toast" id="msgConfig"></div>
 </div>
 <div class="mode" id="mode">Mode iframe (mise en forme limitée)</div>
 <div class="a-coller" id="aColler" hidden>
  <div class="a-coller-tete"><b>Question copiée : cliquez dans le chat ci-dessous, puis Ctrl+V et Entrée</b>
   <button type="button" class="icone-btn" id="btnFermerColler" aria-label="Fermer"><i data-ic="fermer"></i></button></div>
  <div class="a-coller-texte" id="aCollerTexte"></div>
  <div class="a-coller-pied"><button type="button" class="btn petit" id="btnRecopier">Copier à nouveau</button>
   <span>Le mode iframe ne permet pas l'envoi automatique : renseignez le secret Direct Line (bouton « Changer l'agent ») pour envoyer directement.</span></div>
 </div>
 <div id="webchat"></div>
 <div class="attente" id="attente"><span class="points"><i></i><i></i><i></i></span><span id="attenteTxt">BaliseIA analyse les données…</span></div>
 <div class="questions">
  <h4>Questions suggérées</h4>
  <div class="liste" id="lQuestions"></div>
  <div class="toast" id="toast"></div>
 </div>
</aside>

<script>
/* ====================== Configuration de l'agent ====================== */
// Secret de démonstration – ne pas publier ce fichier ni le versionner ; régénérer le secret après l'événement.
const DIRECTLINE_SECRET = "__DIRECTLINE_SECRET__";
const COPILOT_URL = "https://copilotstudio.microsoft.com/environments/28ed4c89-5dbb-e819-bfa5-dfb4f8150e0f/bots/cr8ee_baliseiav2_RgZI7Z/webchat?__version__=2&enableFileAttachment=false&cliAgent=true";
const WEBCHAT_JS = "https://cdn.botframework.com/botframework-webchat/latest/webchat.js";
/* Domaines Direct Line essayés dans l'ordre : domaine par défaut (directline.botframework.com), puis Europe */
const DOMAINES_DIRECTLINE = [null, "https://europe.directline.botframework.com/v3/directline"];
const DELAI_CONNEXION_MS = 20000;
const DELAI_MAX_REPONSE_MS = 90000;
const CLE_SECRET = "baliseia_directline_secret", CLE_AGENT = "baliseia_agent_url";
const CLE_VALID = "baliseia_validations_v1", CLE_VALIDATEUR = "baliseia_dernier_validateur";
const DATA = __DATA__;

/* ====================== Icônes SVG (trait 1,75 px) ====================== */
const P = {
  jauge:'<path d="M12 14l4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  valider:'<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
  barres:'<path d="M3 3v18h18"/><path d="M7 16v-4"/><path d="M12 16V8"/><path d="M17 16v-7"/>',
  balise:'<circle cx="12" cy="12" r="3.5"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/><path d="m4.9 4.9 2.1 2.1"/><path d="m17 17 2.1 2.1"/><path d="m4.9 19.1 2.1-2.1"/><path d="m17 7 2.1-2.1"/>',
  bouclier:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
  message:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  info:'<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  alerte:'<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  liste:'<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
  cle:'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  horloge:'<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  chrono:'<path d="M10 2h4"/><path d="M12 14l3-3"/><circle cx="12" cy="14" r="8"/>',
  ouvert:'<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
  coche:'<path d="M20 6 9 17l-5-5"/>',
  fermer:'<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  question:'<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  telecharger:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  reinit:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  reglages:'<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>',
  externe:'<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  fleche:'<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  ampoule:'<path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>',
  rejeter:'<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
  envoyer:'<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  rapport:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
  imprimer:'<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  doublon:'<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
};
const ic = (n,cls="") => `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]||""}</svg>`;
function poserIcones(racine=document){ racine.querySelectorAll("i[data-ic]").forEach(i=>{ i.outerHTML=ic(i.dataset.ic); }); }

/* ====================== Sources : Base BaliseIA ====================== */
const SECTIONS = {1:"Règles de calcul",2:"Indicateurs globaux",3:"Classement / score de priorité",4:"Fiches équipement",
  5:"Familles",6:"Sites",7:"Synthèse mensuelle",8:"Causes récurrentes",9:"Pièces et actions",10:"Anomalies",
  11:"Recommandations documentées",12:"Synthèse mensuelle détaillée"};
function texteSource(liste,plus){
  const n=String(liste).split(",").map(Number);
  const t=n.length===1 ? `Source : Base BaliseIA, section ${n[0]} – ${SECTIONS[n[0]]}`
    : `Source : Base BaliseIA, sections ${n.map(x=>`${x} (${SECTIONS[x].toLowerCase()})`).join(", ")}`;
  return plus ? `${t}. ${plus}` : t;
}
const htmlSource = (liste,plus) => { const t=texteSource(liste,plus).replace(/"/g,"&quot;");
  return `<span class="src" tabindex="0" role="note" aria-label="${t}" data-tip="${t}">${ic("info")}</span>`; };
function poserSources(racine=document){ racine.querySelectorAll("span[data-src]").forEach(s=>{ s.outerHTML=htmlSource(s.dataset.src,s.dataset.plus); }); }

/* ====================== Libellés en français ====================== */
const LIB = {
  FEUX_BORD_PISTE:"Feux de bord de piste", FEUX_SEUIL:"Feux de seuil", FEUX_APPROCHE:"Feux d'approche",
  PAPI:"PAPI", REGULATEUR_CCR:"Régulateur CCR",
  connectique:"Connectique", cause_indeterminee:"Cause indéterminée", controle_periodique:"Contrôle périodique",
  lampe_defectueuse:"Lampe défectueuse", alimentation:"Alimentation", usure:"Usure", humidite:"Humidité",
  fusible:"Fusible", module:"Module", lampe:"Lampe", connecteur:"Connecteur", aucune:"Aucune",
  remplacement_lampe:"Remplacement de lampe", remplacement_module:"Remplacement de module", reprise_connexion:"Reprise de connexion",
  inspection:"Inspection", sechage:"Séchage", controle_circuit:"Contrôle du circuit",
  CLOTURE:"Clôturé", EN_COURS:"En cours", FAIBLE:"Faible", MOYENNE:"Moyenne", ELEVEE:"Élevée",
  "DAK-SIM":"Dakar", "NIM-SIM":"Niamey", "ABJ-SIM":"Abidjan"
};
const lib = k => k==null ? "–" : (LIB[k] || String(k).replace(/_/g," "));
const min1 = s => s.charAt(0).toLowerCase()+s.slice(1);
const maj1 = s => s.charAt(0).toUpperCase()+s.slice(1);
const libMin = k => k==="PAPI"||k==="REGULATEUR_CCR" ? lib(k) : min1(lib(k));
const secteur = l => l ? l.replace(/^SECTEUR-/,"secteur ") : "";
/* Article défini et « de » pour les phrases générées */
const ART = {connectique:"la ",cause_indeterminee:"la ",lampe_defectueuse:"la ",alimentation:"l'",usure:"l'",humidite:"l'"};
const avecArticle = t => (ART[t]??"le ")+libMin(t);
const avecDe = t => (/^[aeiouhéè]/i.test(libMin(t)) ? "d'" : "de ")+libMin(t);
/* Textes de la Base : jetons techniques -> français correct, décimales à virgule, identifiants balisés */
const JETONS = [[/\bEN_COURS\b/g,"en cours"],[/\bA_VALIDER\b/g,"à valider"],[/ÉLEVÉE/g,"élevée"],[/\bELEVEE\b/g,"élevée"],[/\bMOYENNE\b/g,"moyenne"],[/\bFAIBLE\b/g,"faible"],
  [/\bcause_indeterminee\b/g,"cause indéterminée"],[/\blampe_defectueuse\b/g,"lampe défectueuse"],[/\bhumidite\b/g,"humidité"],
  [/\bcontrole_periodique\b/g,"contrôle périodique"],[/\bsechage\b/g,"séchage"],[/\bremplacement_lampe\b/g,"remplacement de lampe"],
  [/(?<![A-Z]-)\bDAK-SIM\b(?!-)/g,"Dakar"],[/(?<![A-Z]-)\bNIM-SIM\b(?!-)/g,"Niamey"],[/(?<![A-Z]-)\bABJ-SIM\b(?!-)/g,"Abidjan"],
  [/\bSECTEUR-(\d)/g,"secteur $1"],[/(\d)\.(\d)/g,"$1,$2"],[/incident\(s\)/g,"incidents"],[/ \/100/g,"/100"]];
const esc = s => String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const refs = s => s.replace(/\b((?:EQ|INC|REC)-[A-Z0-9-]*[0-9A-Z])\b/g,'<span class="ref">$1</span>');
/* Accords : 0 -> « aucun incident » / « aucune panne », 1 -> singulier */
const accords = s => s.replace(/\b0 incidents\b/g,"aucun incident").replace(/\b1 incidents\b/g,"1 incident")
  .replace(/\b0 pannes\b/g,"aucune panne").replace(/\b1 pannes\b/g,"1 panne");
const nIncidents = n => n===0 ? "aucun incident" : n===1 ? "1 incident" : `${ni(n)} incidents`;
const texteBase = s => refs(esc(accords(JETONS.reduce((t,[r,v])=>t.replace(r,v),s))));

/* ====================== Règles métier (identiques à prepare_data.py) ====================== */
const SITES = ["DAK-SIM","NIM-SIM","ABJ-SIM"];
const INCOH = {lampe_defectueuse:["sechage"], alimentation:["remplacement_lampe"], humidite:["remplacement_lampe"]};
const C = {bleu:"#0b4f8a", fonce:"#0d2f55", attention:"#e07b2a", critique:"#c0392b"};
const estValide = i => typeof i.duree === "number" && i.duree >= 0;   // règle 2
const estPanne  = i => i.type_panne !== "controle_periodique";         // règle 3
const somme = a => a.reduce((s,x)=>s+x,0);
const moyenne = a => a.length ? somme(a)/a.length : null;
const nf = (v,d=1) => v==null ? "–" : v.toLocaleString("fr-FR",{minimumFractionDigits:d,maximumFractionDigits:d});
const ni = v => v.toLocaleString("fr-FR");
const compter = (arr,f) => arr.reduce((m,x)=>{const k=f(x); m[k]=(m[k]||0)+1; return m;},{});
const fr = d => d.slice(0,10).split("-").reverse().join("/");
const frDH = d => fr(d) + (d.length>10 ? " " + d.slice(11,16) : "");
const moisCourt = m => ["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."][+m.slice(5)-1]+" "+m.slice(2,4);

/* Équipements : valeurs FIGÉES de la Base, section 3 (aucun recalcul) */
const EQ = DATA.equipements.map(e=>({...e, b:e.base})).sort((a,b)=>a.b.rang-b.b.rang);
const EQ_DE = Object.fromEntries(EQ.map(e=>[e.equipement_id,e]));
const estCritique = e => e.criticite==="ELEVEE" && e.b.rang<=5;
const INC_DE = Object.fromEntries(DATA.incidents.map(i=>[i.incident_id,i]));
const REC = DATA.recommandations;
const REC_DE = Object.fromEntries(REC.map(r=>[r.id,r]));
const REC_EQ = Object.fromEntries(REC.filter(r=>r.equipement_id).map(r=>[r.equipement_id,r]));

/* Cause principale : ex aequo affichés ensemble, triés alphabétiquement */
function causes(pannes){
  const c=compter(pannes,i=>i.type_panne), max=Math.max(0,...Object.values(c));
  return {max, types:Object.keys(c).filter(t=>c[t]===max).sort((a,b)=>lib(a).localeCompare(lib(b),"fr"))};
}

/* Anomalies (règle 8) recalculées ; le doublon (supprimé en amont) vient de data.json */
const TYPES_ANO = {
  DOUBLON:{lib:"Doublon",ic:"doublon",ton:"",trt:"Seconde occurrence supprimée des calculs"},
  DUREE_MANQUANTE:{lib:"Durée manquante",ic:"horloge",ton:"",trt:"Comptée dans les fréquences, exclue des durées et du MTTR"},
  DUREE_NEGATIVE:{lib:"Durée négative",ic:"horloge",ton:"",trt:"Comptée dans les fréquences, exclue des durées et du MTTR"},
  INCIDENT_LONG:{lib:"Incident long (> 24 h)",ic:"alerte",ton:"attention",trt:"Conservé dans les calculs, à examiner par l'expert"},
  INCOHERENCE:{lib:"Incohérence panne / action",ic:"question",ton:"",trt:"À vérifier par l'expert (saisie possiblement erronée)"},
  NON_CLOTURE:{lib:"Incident non clôturé",ic:"ouvert",ton:"critique",trt:"Compté dans les fréquences, exclu du MTTR"}
};
function listeAnomalies(inc){
  const ids=new Set(inc.map(i=>i.incident_id)), out=[];
  DATA.anomalies.filter(a=>a.type==="DOUBLON" && ids.has(a.incident_id))
    .forEach(a=>out.push({type:"DOUBLON",i:INC_DE[a.incident_id],detail:"Ligne identique en double dans l'historique"}));
  inc.forEach(i=>{
    const b=i.duree_brute;
    if(b==null) out.push({type:"DUREE_MANQUANTE",i,detail:"Durée d'indisponibilité absente"});
    else if(b<0) out.push({type:"DUREE_NEGATIVE",i,detail:`Durée de ${nf(b)} h (impossible)`});
    if(b>24) out.push({type:"INCIDENT_LONG",i,detail:`Durée de ${nf(b)} h`});
    if((INCOH[i.type_panne]||[]).includes(i.action_corrective))
      out.push({type:"INCOHERENCE",i,detail:`${lib(i.type_panne)} traitée par ${min1(lib(i.action_corrective))}`});
    if(i.statut==="EN_COURS") out.push({type:"NON_CLOTURE",i,detail:"Incident toujours en cours"});
  });
  return out;
}

/* ====================== Validation humaine (localStorage protégé) ====================== */
function lire(cle){ try{ return localStorage.getItem(cle)||""; }catch(e){ return ""; } }
function ecrire(cle,v){ try{ v ? localStorage.setItem(cle,v) : localStorage.removeItem(cle); }catch(e){} }
function chargerValid(){ try{ const v=JSON.parse(lire(CLE_VALID)||"null"); if(v && v.decisions && Array.isArray(v.journal)) return v; }catch(e){} return {decisions:{},journal:[]}; }
let VALID = chargerValid();
const sauverValid = () => ecrire(CLE_VALID, JSON.stringify(VALID));
const DECISIONS = {valider:{code:"validee",lib:"Validée",ton:"valide"}, rejeter:{code:"rejetee",lib:"Rejetée",ton:"rejete"}};
function statutRec(id){
  const d=VALID.decisions[id];
  if(!d) return {code:"a_valider",lib:"À valider",ton:"attention",d:null};
  return d.code==="validee" ? {code:"validee",lib:"Validée",ton:"valide",d} : {code:"rejetee",lib:"Rejetée",ton:"rejete",d};
}
const pastilleRec = id => { const s=statutRec(id); return `<span class="statut ${s.ton}">${s.code==="validee"?ic("coche"):""}${s.lib}${s.d&&s.d.ot?` · ${esc(s.d.ot)}`:""}</span>`; };
/* Ordres de travail : compteur OT-2026-001, 002… conservé dans ce navigateur */
const CLE_OT = "baliseia_compteur_ot";
const OUVERTES = new Set();   // cartes dont le formulaire de décision est déplié
const quandFR = iso => { const d=new Date(iso); return `${d.toLocaleDateString("fr-FR")} à ${d.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}`; };

/* ====================== Graphiques SVG ====================== */
const NS="http://www.w3.org/2000/svg";
function svg(w,h,titre){ const s=document.createElementNS(NS,"svg"); s.setAttribute("viewBox",`0 0 ${w} ${h}`); s.setAttribute("class","graph"); s.setAttribute("role","img"); if(titre) s.setAttribute("aria-label",titre); return s; }
function el(p,tag,attrs,txt){ const e=document.createElementNS(NS,tag); for(const k in attrs) e.setAttribute(k,attrs[k]); if(txt!=null) e.textContent=txt; p.appendChild(e); return e; }
function bulle(e,t){ el(e,"title",{},t); }
function coupe(l){ if(l.length<=11 || !l.includes(" ")) return [l];
  const m=l.split(" "); let best=[l],ecart=1e9;
  for(let k=1;k<m.length;k++){ const a=m.slice(0,k).join(" "), b=m.slice(k).join(" "), e=Math.abs(a.length-b.length); if(e<ecart){ecart=e;best=[a,b];} }
  return best; }
/* Toutes les barres d'un graphique en bleu, la première plus foncée */
const couleurRang = k => k===0 ? C.fonce : C.bleu;

function barresH(id,items,{G=110,W=440}={}){
  const box=document.getElementById(id); box.innerHTML="";
  if(!items.length){ box.innerHTML='<div class="vide">Aucune panne</div>'; return; }
  const lh=items.length>6?26:32, bh=lh-12, H=items.length*lh+8, max=Math.max(...items.map(i=>i.v));
  const s=svg(W,H);
  items.forEach((it,k)=>{
    const y=k*lh+4, w=(W-G-34)*it.v/max;
    el(s,"text",{x:G-8,y:y+bh/2+8,"text-anchor":"end","font-size":11.5,fill:"#1c2733"},it.l);
    const r=el(s,"rect",{x:G,y:y+4,width:Math.max(w,2),height:bh,rx:3,fill:couleurRang(k)}); bulle(r,`${it.l} : ${it.v}`);
    el(s,"text",{x:G+w+6,y:y+bh/2+8,"font-size":12,"font-weight":600,fill:"#0d2f55"},it.v);
  });
  box.appendChild(s);
}
function barresV(id,items,W=440){
  const box=document.getElementById(id); box.innerHTML="";
  if(!items.length){ box.innerHTML='<div class="vide">Aucune donnée</div>'; return; }
  const H=230,B=46,T=22, max=Math.max(...items.map(i=>i.v),1), bw=(W-30)/items.length;
  const s=svg(W,H);
  el(s,"line",{x1:15,x2:W-15,y1:H-B,y2:H-B,stroke:"#c9d3dd"});
  items.forEach((it,k)=>{
    const h=(H-B-T)*it.v/max, w=Math.min(bw*0.6,72), x=15+k*bw+(bw-w)/2;
    const r=el(s,"rect",{x,y:H-B-h,width:w,height:h,rx:3,fill:couleurRang(k)}); bulle(r,`${it.l} : ${it.v}`);
    el(s,"text",{x:x+w/2,y:H-B-h-6,"text-anchor":"middle","font-size":13,"font-weight":600,fill:"#0d2f55"},it.v);
    coupe(it.l).forEach((ligne,n)=>el(s,"text",{x:x+w/2,y:H-B+16+n*13,"text-anchor":"middle","font-size":11.5,fill:"#1c2733"},ligne));
  });
  box.appendChild(s);
}
function courbe(id,pts,{W=440,H=230,pas=3}={}){
  const box=document.getElementById(id); box.innerHTML="";
  const L=26,R=12,T=34,B=30, max=Math.max(...pts.map(p=>p.v),1);
  const s=svg(W,H), dx=(W-L-R)/Math.max(pts.length-1,1), y=v=>H-B-(H-B-T)*v/max, mo=m=>`${m.slice(5)}/${m.slice(2,4)}`;
  for(let g=0;g<=4;g++){ const v=Math.round(max*g/4), yy=y(v);
    el(s,"line",{x1:L,x2:W-R,y1:yy,y2:yy,stroke:"#e7ecf1"});
    el(s,"text",{x:L-5,y:yy+4,"text-anchor":"end","font-size":9.5,fill:"#6b7785"},v); }
  const d=pts.map((p,k)=>`${k?"L":"M"}${L+k*dx},${y(p.v)}`).join(" ");
  el(s,"path",{d:`${d} L${L+(pts.length-1)*dx},${H-B} L${L},${H-B} Z`,fill:"rgba(11,79,138,.07)"});
  el(s,"path",{d,fill:"none",stroke:C.bleu,"stroke-width":2,"stroke-linejoin":"round"});
  pts.forEach((p,k)=>{
    const pic=p.v===max && max>0, cx=L+k*dx;
    const c=el(s,"circle",{cx,cy:y(p.v),r:pic?5:2.8,fill:pic?C.attention:C.bleu}); bulle(c,`${moisCourt(p.m)} : ${p.v} pannes`);
    if(k%pas===0 || k===pts.length-1) el(s,"text",{x:cx,y:H-B+16,"text-anchor":"middle","font-size":9.5,fill:"#6b7785"},mo(p.m));
  });
  const pics=pts.map((p,k)=>({...p,k})).filter(p=>p.v===max && max>0);
  if(pics.length){
    const cx=L+dx*(pics[0].k+pics[pics.length-1].k)/2;
    el(s,"text",{x:Math.min(Math.max(cx,90),W-90),y:T-12,"text-anchor":"middle","font-size":11,"font-weight":600,fill:C.attention},
      `Pic : ${max} pannes (${pics.map(p=>moisCourt(p.m)).join(" et ")})`);
  }
  box.appendChild(s);
}
function moisPeriode(){
  const [a,b]=DATA.meta.periode.map(d=>d.slice(0,7)); const out=[]; let [y,m]=a.split("-").map(Number);
  while(true){ const k=`${y}-${String(m).padStart(2,"0")}`; out.push(k); if(k>=b) break; m++; if(m>12){m=1;y++;} }
  return out;
}

/* ====================== État ====================== */
let SITE = "";
const incFiltres = () => DATA.incidents.filter(i=>!SITE||i.site===SITE);
const eqFiltres = () => EQ.filter(e=>!SITE||e.site===SITE);
const recFiltrees = () => REC.filter(r=>!r.site || !SITE || r.site===SITE);

/* ====================== Accueil (cockpit) ====================== */
function phrasesARetenir(inc,pannes){
  const out=[], toutes=DATA.incidents.filter(estPanne);
  /* 1. Concentration par site et part des équipements prioritaires (rang Base ≤ 10) */
  const ps=compter(toutes,i=>i.site), site=SITE || SITES.slice().sort((a,b)=>ps[b]-ps[a])[0];
  const top10=EQ.filter(e=>e.b.rang<=10 && e.site===site).length, pct=Math.round(100*ps[site]/toutes.length);
  out.push(`${lib(site)} ${SITE?"représente":"concentre"} ${ps[site]} des ${toutes.length} pannes${SITE?" du réseau":""} (${pct} %) et ${top10} des 10 équipements les plus prioritaires.`);
  /* 2. Première cause de panne (ex aequo gérés) et équipement le plus touché par cette cause */
  const c=causes(pannes);
  if(c.max){
    let best=null;
    c.types.forEach(t=>{ const parEq=compter(pannes.filter(i=>i.type_panne===t),i=>i.equipement_id);
      Object.entries(parEq).forEach(([e,n])=>{ if(!best || n>best.n || (n===best.n && EQ_DE[e].b.score>EQ_DE[best.e].b.score)) best={t,e,n}; }); });
    out.push(c.types.length===1
      ? `${maj1(avecArticle(c.types[0]))} est la 1re cause de panne (<span id="causePrincipale">${c.max}</span>) : ${best.n} occurrences sur ${refs(best.e)}.`
      : `Les 1res causes de panne sont à égalité : <span id="causePrincipale">${c.types.map(libMin).join(" / ")} (${c.max} chacune)</span> ; ${best.n} occurrences ${avecDe(best.t)} sur ${refs(best.e)}.`);
  }
  /* 3. Incidents encore ouverts malgré une intervention */
  const ouverts=inc.filter(i=>i.statut==="EN_COURS"), delais=[...new Set(ouverts.map(i=>i.delai_intervention_h).filter(v=>v!=null))];
  out.push(!ouverts.length ? "Aucun incident ouvert : tous les incidents de la période sont clôturés."
    : delais.length===1 ? (ouverts.length===1 ? `1 incident est encore ouvert alors qu'une intervention a eu lieu ${nf(delais[0],0)} h après son début.`
        : `${ouverts.length} incidents sont encore ouverts alors qu'une intervention a eu lieu ${nf(delais[0],0)} h après chacun.`)
    : `${ouverts.length} incidents sont encore ouverts alors qu'une intervention a eu lieu en moyenne ${nf(moyenne(ouverts.map(i=>i.delai_intervention_h)))} h après leur début.`);
  return out;
}
function constatCourt(r){
  if(!r.equipement_id) return texteBase(r.constat.split(/(?<=\.)\s/)[0].replace(/\.$/,""));
  const e=EQ_DE[r.equipement_id];
  return `Rang ${e.b.rang}/30 · ${e.b.pannes} pannes · ${nf(e.b.duree)} h · cause : ${libMin(e.b.cause)}`;
}
const actionCourte = r => texteBase(maj1(r.recommandation.split(";")[0].trim().replace(/\.$/,"")));

function rendreResume(inc,pannes,valides,enCours){
  document.getElementById("retenir").innerHTML=phrasesARetenir(inc,pannes).map(p=>`<li>${p}</li>`).join("");
  const K=[
    ["liste",ni(inc.length),"Incidents uniques",""],
    ["cle",ni(pannes.length),"Pannes (hors contrôles périodiques)",""],
    ["horloge",ni(Math.round(somme(valides.map(i=>i.duree))))+" h","Heures d'indisponibilité totale",""],
    ["chrono",nf(moyenne(valides.map(i=>i.duree)))+" h","Durée moyenne d'indisponibilité",""],
    ["ouvert",ni(enCours),"Incidents en cours","critique"]];
  document.getElementById("kpis").innerHTML=K.map(([n,v,l,cl])=>
    `<div class="carte kpi ${cl}"><div class="pic">${ic(n)}</div><div><div class="val">${v}</div><div class="lib">${l}</div></div></div>`).join("");
  const enAttente=recFiltrees().filter(r=>statutRec(r.id).code==="a_valider").slice(0,5);
  document.getElementById("tActions").innerHTML = enAttente.length ? enAttente.map(r=>`<tr>
     <td class="nowrap"><span class="rec-id">${r.id}</span> ${r.equipement_id?`<b>${r.equipement_id}</b>`:esc(r.titre)}</td>
     <td>${constatCourt(r)}</td><td>${actionCourte(r)}</td>
     <td class="nowrap"><button type="button" class="btn petit prim" data-examiner="${r.id}">Examiner ${ic("fleche")}</button></td></tr>`).join("")
    : `<tr><td colspan="4" class="vide">Toutes les recommandations ont été examinées.</td></tr>`;
  const pm=compter(pannes,i=>i.mois);
  courbe("gMiniMois",moisPeriode().map(m=>({m,v:pm[m]||0})),{W:640,H:200,pas:2});
  const nb=compter(listeAnomalies(inc),a=>a.type);
  document.getElementById("lAlertes").innerHTML=Object.keys(TYPES_ANO).filter(t=>nb[t])
    .map(t=>`<li class="${TYPES_ANO[t].ton}">${ic(TYPES_ANO[t].ic)}<span>${TYPES_ANO[t].lib}</span><b>${nb[t]}</b></li>`).join("") || "<li>Aucune anomalie</li>";
}

/* ====================== Recommandations ====================== */
function carteRec(r){
  const s=statutRec(r.id), e=r.equipement_id?EQ_DE[r.equipement_id]:null, ouvert=OUVERTES.has(r.id);
  const ident = e ? `<b>${r.equipement_id}</b><small>${lib(r.famille)} · ${lib(r.site)}, ${secteur(r.localisation)} · rang ${e.b.rang}/30</small>`
                  : `<b>${esc(r.titre)}</b><small>Recommandation transverse</small>`;
  const trace = s.d ? `<div class="trace ${s.code==="validee"?"valide":""}">${s.lib} le ${quandFR(s.d.quand)} par <b>${esc(s.d.par)}</b>${s.d.commentaire?` – « ${esc(s.d.commentaire)} »`:""}${s.d.ot?` · ordre de travail <b>${esc(s.d.ot)}</b> généré le ${quandFR(s.d.otQuand)}`:""}</div>` : "";
  /* Boutons de la carte : Décider / Demander plus d'infos ; après validation : ordre de travail */
  let boutons = `<button type="button" class="btn ${s.code==="a_valider"?"prim":""}" data-action="decider">${ic("valider")}${s.code==="a_valider"?"Décider":"Modifier la décision"}</button>`;
  if(s.code==="validee") boutons = (s.d.ot
      ? `<button type="button" class="btn ok" data-action="ot">${ic("rapport")}Ouvrir l'ordre de travail</button>
         <a class="btn" href="${mailtoOT(r)}" data-mailto="${r.id}">${ic("envoyer")}Envoyer au chef d'équipe</a>`
      : `<button type="button" class="btn ok" data-action="ot">${ic("rapport")}Générer l'ordre de travail</button>`) + boutons;
  return `<article class="carte rec s-${s.ton}${ouvert?" form-ouvert":""}" id="rec-${r.id}" data-rec="${r.id}">
   <header><div class="ident"><span class="rec-id">${r.id}</span> ${ident}</div>${pastilleRec(r.id)}</header>
   <dl><dt>Constat</dt><dd>${texteBase(maj1(r.constat))}</dd><dt>Recommandation</dt><dd>${texteBase(maj1(r.recommandation))}</dd>
     <dt>Statut</dt><dd>${s.code==="a_valider"?"À valider par l'expert métier":s.lib+" par l'expert métier"}</dd></dl>
   ${trace}
   <div class="actions-carte">${boutons}
    <button type="button" class="btn" data-action="infos">${ic("question")}Demander plus d'infos</button></div>
   <form novalidate>
    <label><span>Nom du validateur <span class="req" aria-hidden="true">*</span></span><input name="nom" required autocomplete="name" value="${esc(lire(CLE_VALIDATEUR))}"></label>
    <label>Commentaire<textarea name="commentaire" rows="1"></textarea></label>
    <div class="actions">
     <button type="button" class="btn ok" data-action="valider">${ic("coche")}Valider</button>
     <button type="button" class="btn" data-action="rejeter">${ic("rejeter")}Rejeter</button>
     <button type="button" class="btn" data-action="annuler">Annuler</button>
     <span class="msg" role="alert"></span>
    </div>
   </form></article>`;
}
function rendreRecommandations(){
  const recs=recFiltrees(), eqs=recs.filter(r=>r.equipement_id), tr=recs.filter(r=>!r.equipement_id);
  document.getElementById("nbRecEq").textContent=`(${eqs.length})`;
  document.getElementById("recsEq").innerHTML=eqs.map(carteRec).join("") || '<div class="vide">Aucune recommandation pour ce site.</div>';
  document.getElementById("recsT").innerHTML=tr.map(carteRec).join("");
  rendreJournal();
}
function rendreJournal(){
  document.getElementById("nbJournal").textContent=`(${VALID.journal.length})`;
  document.getElementById("tJournal").innerHTML = VALID.journal.length ? VALID.journal.map(j=>`<tr>
    <td class="nowrap">${quandFR(j.quand)}</td><td>${esc(j.par)}</td><td class="nowrap"><span class="rec-id">${j.rec}</span> ${j.equipement?esc(j.equipement):""}</td>
    <td><span class="statut ${j.decision==="Validée"?"valide":j.decision==="OT généré"?"info":"rejete"}">${j.decision}</span></td><td class="nowrap">${esc(j.ot||"")}</td><td>${esc(j.commentaire||"")}</td></tr>`).join("")
    : '<tr><td colspan="6" class="vide">Aucune décision enregistrée.</td></tr>';
}
function decider(id,action,form){
  const nom=form.nom.value.trim(), msg=form.querySelector(".msg");
  if(!nom){ form.nom.classList.add("erreur"); form.nom.focus(); msg.textContent="Le nom du validateur est obligatoire."; return; }
  const D=DECISIONS[action], quand=new Date().toISOString(), commentaire=form.commentaire.value.trim(), r=REC_DE[id];
  const prec=VALID.decisions[id], garderOT = prec && prec.ot && D.code==="validee";   // une revalidation conserve l'OT déjà émis
  VALID.decisions[id]={code:D.code,par:nom,quand,commentaire,ot:garderOT?prec.ot:"",otQuand:garderOT?prec.otQuand:""};
  VALID.journal.unshift({quand,par:nom,rec:id,equipement:r.equipement_id||r.titre,decision:D.lib,commentaire,ot:garderOT?prec.ot:""});
  sauverValid(); ecrire(CLE_VALIDATEUR,nom); OUVERTES.delete(id);
  const carte=document.getElementById("rec-"+id); carte.outerHTML=carteRec(r);
  rendreJournal(); rendre(false);
}
/* ---- Ordres de travail ---- */
const texteBrut = s => accords(JETONS.reduce((t,[r,v])=>t.replace(r,v),s));
function piecesAPreparer(eqId){
  const c=compter(DATA.incidents.filter(i=>i.equipement_id===eqId && i.piece_remplacee && i.piece_remplacee.toLowerCase()!=="aucune"),i=>i.piece_remplacee);
  return Object.entries(c).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([k,n])=>({lib:lib(k),n}));
}
function mailtoOT(r){
  const d=VALID.decisions[r.id]; if(!d||!d.ot) return "#";
  const e=r.equipement_id?EQ_DE[r.equipement_id]:null, action=texteBrut(maj1(r.recommandation.split(";")[0].trim().replace(/\.$/,"")));
  const objet=`${d.ot} – ${r.equipement_id||r.titre} – ${action}`;
  const pieces=e?piecesAPreparer(e.equipement_id).map(p=>`${p.lib} (${p.n})`).join(", ")||"aucune pièce identifiée":"sans objet";
  const corps=[`Bonjour,`,``,`Ordre de travail ${d.ot} – référence ${r.id} (validée par ${d.par} le ${quandFR(d.quand)}).`,``,
    e?`Équipement : ${e.equipement_id} – ${lib(e.famille)} – ${lib(e.site)}, ${secteur(e.localisation)} – criticité ${lib(e.criticite).toLowerCase()}, score ${nf(e.b.score)}/100, rang ${e.b.rang}/30.`:`Recommandation transverse : ${r.titre}.`,
    `Constat : ${texteBrut(maj1(r.constat))}`,`Action à réaliser : ${texteBrut(maj1(r.recommandation))}`,`Pièces à préparer : ${pieces}.`,
    d.commentaire?`Commentaire du validateur : ${d.commentaire}`:"",``,`Merci d'assigner un technicien et une date d'intervention.`,``,
    `BaliseIA – prototype, données fictives. Toute recommandation doit être validée par un expert métier.`].filter(x=>x!==null).join("\n");
  return `mailto:?subject=${encodeURIComponent(objet)}&body=${encodeURIComponent(corps)}`;
}
function genererOT(id){
  const d=VALID.decisions[id], r=REC_DE[id]; if(!d || d.code!=="validee") return;
  if(!d.ot){
    let n=parseInt(lire(CLE_OT)||"0",10); if(!(n>=0)) n=0; n++; ecrire(CLE_OT,String(n));
    d.ot=`OT-2026-${String(n).padStart(3,"0")}`; d.otQuand=new Date().toISOString();
    const val=VALID.journal.find(j=>j.rec===id && j.decision==="Validée"); if(val) val.ot=d.ot;   // la colonne « N° OT » se remplit
    VALID.journal.unshift({quand:d.otQuand,par:d.par,rec:id,equipement:r.equipement_id||r.titre,decision:"OT généré",commentaire:"",ot:d.ot});
    sauverValid();
    document.getElementById("rec-"+id).outerHTML=carteRec(r); rendreJournal(); rendre(false);
  }
  ouvrirFicheOT(id);
}
function ouvrirFicheOT(id){
  const d=VALID.decisions[id], r=REC_DE[id], e=r.equipement_id?EQ_DE[r.equipement_id]:null;
  const logo=document.querySelector(".encart .logo"), pieces=e?piecesAPreparer(e.equipement_id):[];
  const ligne=(l,v)=>`<tr><th>${l}</th><td>${v}</td></tr>`;
  const html=`<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>${d.ot} – Ordre de travail BaliseIA</title><style>
  @page{size:A4;margin:14mm}
  *{box-sizing:border-box} body{margin:0;background:#eef1f4;font:10.5pt/1.45 "Segoe UI",Arial,sans-serif;color:#1c2733}
  .barre{position:sticky;top:0;background:#0d2f55;color:#fff;padding:10px 16px;display:flex;align-items:center;gap:12px}
  .barre b{flex:1} .barre button{font:inherit;border:0;border-radius:6px;padding:7px 14px;background:#fff;color:#0d2f55;font-weight:600;cursor:pointer}
  .feuille{width:210mm;min-height:297mm;margin:16px auto;background:#fff;padding:14mm;box-shadow:0 2px 10px rgba(13,47,85,.15)}
  header{display:flex;align-items:center;gap:12px;border-bottom:2px solid #0b4f8a;padding-bottom:4mm;margin-bottom:5mm}
  header img{width:16mm;height:16mm} header h1{margin:0;font-size:17pt;color:#0d2f55;flex:1}
  .proto{border:1px solid #f3d2b3;background:#fdf1e6;color:#8a4410;border-radius:4px;padding:1.5mm 3mm;font-size:9pt;font-weight:600;white-space:nowrap}
  h2{font-size:11.5pt;color:#0d2f55;margin:5mm 0 2mm;border-bottom:1px solid #dfe5eb;padding-bottom:1mm}
  table{width:100%;border-collapse:collapse} th,td{text-align:left;vertical-align:top;padding:1.6mm 2.5mm;border:1px solid #dfe5eb}
  th{width:38%;background:#eef4fa;color:#0d2f55;font-weight:600} .grille{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
  .ref{font-family:Consolas,monospace;font-size:.92em;white-space:nowrap}
  .vide{height:9mm} .obs{height:30mm} .sig{height:28mm;vertical-align:bottom;color:#6b7785;font-size:9pt}
  .num{font-size:14pt;font-weight:700;color:#0b4f8a}
  footer{margin-top:6mm;font-size:8.5pt;color:#6b7785;border-top:1px solid #dfe5eb;padding-top:2mm}
  @media print{body{background:#fff}.barre{display:none}.feuille{width:auto;min-height:0;margin:0;padding:0;box-shadow:none}
    *{-webkit-print-color-adjust:exact;print-color-adjust:exact} table,.grille{break-inside:avoid}}
  </style></head><body>
  <div class="barre"><b>${d.ot} – fiche d'intervention</b><button type="button" onclick="window.print()">Imprimer / Enregistrer en PDF</button></div>
  <div class="feuille">
   <header>${logo?`<img src="${logo.src}" alt="Logo ASECNA">`:""}<h1>Ordre de travail – Maintenance du balisage</h1><span class="proto">Prototype – données fictives</span></header>
   <table>${ligne("N° d'ordre de travail",`<span class="num" id="numOT">${d.ot}</span>`)}${ligne("Date d'émission",quandFR(d.otQuand))}${ligne("Référence",`<span class="ref">${r.id}</span> – Base BaliseIA, section 11`)}</table>
   ${e?`<h2>Équipement</h2><table id="blocEquipement">${ligne("Identifiant",`<span class="ref">${e.equipement_id}</span>`)}${ligne("Famille",lib(e.famille))}${ligne("Site",lib(e.site))}${ligne("Secteur",maj1(secteur(e.localisation)))}${ligne("Criticité",lib(e.criticite))}${ligne("Score de priorité",`${nf(e.b.score)} / 100`)}${ligne("Rang",`${e.b.rang} / 30`)}</table>`
      :`<h2>Objet</h2><table>${ligne("Recommandation transverse",esc(r.titre))}</table>`}
   <h2>Constat</h2><p>${texteBase(maj1(r.constat))}</p>
   <h2>Action à réaliser</h2><p>${texteBase(maj1(r.recommandation))}</p>
   <h2>Pièces à préparer</h2><p id="pieces">${e?(pieces.length?pieces.map(p=>`${p.lib} (${p.n} remplacement${p.n>1?"s":""} sur les incidents de l'équipement)`).join(" ; "):"Aucune pièce identifiée dans l'historique."):"Sans objet (recommandation transverse)."}</p>
   <h2>Intervention</h2><table>${ligne("Technicien assigné",`<div class="vide"></div>`)}${ligne("Date prévue",`<div class="vide"></div>`)}${ligne("Observations",`<div class="obs"></div>`)}</table>
   <h2>Validation de la recommandation</h2><table>${ligne("Validée par",esc(d.par))}${ligne("Date et heure",quandFR(d.quand))}${ligne("Commentaire",d.commentaire?esc(d.commentaire):"–")}</table>
   <h2>Signatures</h2><div class="grille"><table><tr><th>Chef d'équipe</th></tr><tr><td class="sig">Nom, date et signature</td></tr></table>
     <table><tr><th>Technicien</th></tr><tr><td class="sig">Nom, date et signature</td></tr></table></div>
   <footer>BaliseIA – ${d.ot} – Prototype Innovation Days 2026, données fictives : ne pas utiliser pour la maintenance réelle. Toute recommandation doit être validée par un expert métier.</footer>
  </div></body></html>`;
  const w=window.open("","_blank");
  if(!w){ alert("La fenêtre de l'ordre de travail a été bloquée par le navigateur : autorisez les fenêtres pour ce fichier."); return; }
  w.document.open(); w.document.write(html); w.document.close();
}
function exporterJournal(){
  const cel = v => { v=String(v??""); return /[";\n]/.test(v) ? `"${v.replace(/"/g,'""')}"` : v; };
  const lignes=[["Date","Heure","Validateur","Recommandation","Équipement / sujet","Décision","Commentaire","N° OT"]]
    .concat(VALID.journal.slice().reverse().map(j=>{ const d=new Date(j.quand);
      return [d.toLocaleDateString("fr-FR"),d.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"}),j.par,j.rec,j.equipement,j.decision,j.commentaire,j.ot||""]; }));
  const csv="﻿"+lignes.map(l=>l.map(cel).join(";")).join("\r\n");
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download=`journal_validation_BaliseIA_${new Date().toISOString().slice(0,10)}.csv`; document.body.appendChild(a); a.click();
  setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); },500);
}
document.getElementById("v-recommandations").addEventListener("click",ev=>{
  const b=ev.target.closest("button[data-action]"); if(!b) return;
  const carte=b.closest("[data-rec]"), id=carte.dataset.rec, form=carte.querySelector("form"), a=b.dataset.action;
  if(a==="infos") return envoyer(`Explique-moi la recommandation ${id} et les incidents qui la justifient.`);
  if(a==="decider"){ OUVERTES.add(id); carte.classList.add("form-ouvert"); return form.nom.focus(); }
  if(a==="annuler"){ OUVERTES.delete(id); carte.classList.remove("form-ouvert"); form.querySelector(".msg").textContent=""; form.nom.classList.remove("erreur"); return; }
  if(a==="ot") return genererOT(id);
  decider(id,a,form);
});
document.getElementById("v-recommandations").addEventListener("input",ev=>{ if(ev.target.name==="nom"){ ev.target.classList.remove("erreur"); ev.target.form.querySelector(".msg").textContent=""; } });
document.getElementById("btnExport").onclick=exporterJournal;
document.getElementById("btnReset").onclick=()=>{
  if(!confirm("Effacer toutes les décisions et le journal de validation de cette démonstration ?")) return;
  VALID={decisions:{},journal:[]}; sauverValid(); ecrire(CLE_OT,""); OUVERTES.clear();   // compteur d'OT remis à 001
  rendreRecommandations(); rendre(false);
};

/* ====================== Rapports ====================== */
const MOIS_LONG=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
const moisLong = m => `${MOIS_LONG[+m.slice(5)-1]} ${m.slice(0,4)}`;
const moisPrec = m => { let [y,k]=m.split("-").map(Number); k--; if(!k){k=12;y--;} return `${y}-${String(k).padStart(2,"0")}`; };
let RAPPORT=null;
(function initRapports(){
  const sel=document.getElementById("rapPeriode");
  sel.innerHTML='<option value="">Toute la période</option>'+moisPeriode().map(m=>`<option value="${m}">${m} – ${moisLong(m)}</option>`).join("");
})();
/* Indicateurs d'une période (règles de prepare_data.py) */
function indicateurs(inc){
  const pannes=inc.filter(estPanne), valides=inc.filter(estValide), clos=inc.filter(i=>i.statut==="CLOTURE"&&estValide(i));
  return {incidents:inc.length, pannes:pannes.length, heures:somme(valides.map(i=>i.duree)), moyenne:moyenne(valides.map(i=>i.duree)),
          mttr:moyenne(clos.map(i=>i.duree)), encours:inc.filter(i=>i.statut==="EN_COURS").length};
}
const IND=[["incidents","Incidents",v=>ni(v),0],["pannes","Pannes hors contrôles périodiques",v=>ni(v),0],
  ["heures","Heures d'indisponibilité",v=>nf(v)+" h",1],["moyenne","Durée moyenne d'indisponibilité",v=>nf(v)+" h",1],
  ["mttr","MTTR (incidents clôturés)",v=>nf(v)+" h",1],["encours","Incidents en cours",v=>ni(v),0]];
function delta(v,p,dec){
  if(p==null||v==null) return '<span class="secondaire">–</span>';
  const d=Math.round((v-p)*10**dec)/10**dec;
  if(!d) return '<span class="delta baisse">= stable</span>';
  const t=(d>0?"+":"−")+(dec?nf(Math.abs(d))+" h":ni(Math.abs(d)));   // dec=1 : indicateurs en heures
  return `<span class="delta ${d>0?"hausse":"baisse"}">${d>0?"▲":"▼"} ${t}</span>`;
}
function phrasesRapport(R){
  const out=[], I=R.ind, pm=R.parMois, max=Math.max(...Object.values(pm)), lieu=R.site?` à ${lib(R.site)}`:"";
  if(R.mois){
    const p=I.pannes, pp=R.prec?R.prec.pannes:null, pic=p===max&&max>0;
    let fin=pic?", soit le pic de la période":"";
    if(!pic && pp) fin=`, soit une ${p>=pp?"hausse":"baisse"} de ${Math.abs(Math.round(100*(p-pp)/pp))} %`;
    out.push(`En ${moisLong(R.mois)}, ${p} panne${p>1?"s ont été enregistrées":" a été enregistrée"}${lieu}${pp!=null?` (contre ${pp} en ${MOIS_LONG[+R.moisPrec.slice(5)-1]})`:""}${fin}.`);
  } else {
    const pics=Object.keys(pm).filter(m=>pm[m]===max).sort();
    out.push(`Du ${fr(DATA.meta.periode[0])} au ${fr(DATA.meta.periode[1])}, ${I.pannes} pannes ont été enregistrées${lieu} ; le pic mensuel atteint ${max} pannes (${pics.map(moisLong).join(" et ")}).`);
  }
  if(I.incidents) out.push(`Les ${I.incidents} incidents ont représenté ${nf(I.heures)} h d'indisponibilité, avec une durée moyenne de ${nf(I.moyenne)} h${R.prec&&R.prec.moyenne!=null?` (${nf(R.prec.moyenne)} h le mois précédent)`:""} et un MTTR de ${nf(I.mttr)} h sur les incidents clôturés.`);
  const c=causes(R.pannes);
  if(c.max) out.push(c.types.length===1 ? `${maj1(avecArticle(c.types[0]))} est la 1re cause de panne (${c.max} sur ${I.pannes}).`
    : `Les 1res causes de panne sont à égalité : ${c.types.map(libMin).join(" / ")} (${c.max} chacune).`);
  if(!R.site){
    const ps=compter(R.pannes,i=>i.site), s=Object.keys(ps).sort((a,b)=>ps[b]-ps[a])[0];
    if(s) out.push(`${lib(s)} est le site le plus touché, avec ${ps[s]} pannes sur ${I.pannes} (${Math.round(100*ps[s]/I.pannes)} %).`);
  } else {
    const pe=compter(R.pannes,i=>i.equipement_id), e=Object.keys(pe).sort((a,b)=>pe[b]-pe[a]||EQ_DE[b].b.score-EQ_DE[a].b.score)[0];
    if(e) out.push(`${e} est l'équipement le plus touché du site sur la période (${pe[e]} panne${pe[e]>1?"s":""}).`);
  }
  out.push(I.encours ? `${I.encours} incident${I.encours>1?"s":""} de la période ${I.encours>1?"sont":"est"} encore en cours et ${R.anomalies.length} anomalie${R.anomalies.length>1?"s":""} de données ${R.anomalies.length>1?"ont été relevées":"a été relevée"} (section 6).`
    : `Tous les incidents de la période sont clôturés ; ${R.anomalies.length} anomalie${R.anomalies.length>1?"s":""} de données relevée${R.anomalies.length>1?"s":""} (section 6).`);
  return out.slice(0,5);
}
function statutTexte(id){
  const s=statutRec(id);
  if(!s.d) return {ton:"attention",txt:"À valider"};
  return {ton:s.ton,txt:`${s.lib} par ${esc(s.d.par)} le ${quandFR(s.d.quand)}${s.d.ot?` · OT n° ${esc(s.d.ot)}`:""}`};
}
function tableau(entetes,lignes,classes=[],largeurs=null){
  const court=lignes.length<=12;   // tableau court : jamais coupé entre deux pages
  return `<table class="rt${court?" court":""}"${largeurs?' style="table-layout:fixed"':""}>${largeurs?`<colgroup>${largeurs.map(w=>`<col style="width:${w}">`).join("")}</colgroup>`:""}<thead><tr>${entetes.map((h,k)=>`<th class="${classes[k]||""}">${h}</th>`).join("")}</tr></thead><tbody>${
    lignes.length?lignes.map(l=>`<tr>${l.map((c,k)=>`<td class="${classes[k]||""}">${c}</td>`).join("")}</tr>`).join(""):`<tr><td colspan="${entetes.length}" class="secondaire">Aucun élément sur la période.</td></tr>`}</tbody></table>`;
}
/* Petit graphique en barres intégré au tableau (la première barre plus foncée) */
const barre = (n,total,k) => { const pct=total?Math.round(100*n/total):0;
  return `<span class="barre-cel" aria-hidden="true"><i style="width:${total?100*n/total:0}%;background:${k===0?C.fonce:C.bleu}"></i></span>${pct} %`; };
function barresMois(id,pts,sel){
  const box=document.getElementById(id); box.innerHTML="";
  const W=640,H=200,L=24,B=30,T=22, max=Math.max(1,...pts.map(p=>p.v)), bw=(W-L-8)/pts.length;
  const s=svg(W,H,"Pannes par mois");
  for(let g=0;g<=3;g++){ const v=Math.round(max*g/3), y=H-B-(H-B-T)*v/max;
    el(s,"line",{x1:L,x2:W-4,y1:y,y2:y,stroke:"#e7ecf1"}); el(s,"text",{x:L-4,y:y+3,"text-anchor":"end","font-size":9,fill:"#6b7785"},v); }
  pts.forEach((p,k)=>{ const h=(H-B-T)*p.v/max, x=L+k*bw+bw*.15, w=bw*.7, actif=p.m===sel;
    const r=el(s,"rect",{x,y:H-B-h,width:w,height:Math.max(h,1),rx:2,fill:actif?C.fonce:(sel?"#9fbbd6":C.bleu)}); bulle(r,`${moisLong(p.m)} : ${p.v} pannes`);
    if(actif||!sel) el(s,"text",{x:x+w/2,y:H-B-h-4,"text-anchor":"middle","font-size":actif?11:9,"font-weight":actif?700:400,fill:"#0d2f55"},p.v);
    el(s,"text",{x:x+w/2,y:H-B+13,"text-anchor":"middle","font-size":8.5,"font-weight":actif?700:400,fill:actif?"#0d2f55":"#6b7785"},`${p.m.slice(5)}/${p.m.slice(2,4)}`); });
  box.appendChild(s);
}
function genererRapport(){
  const mois=document.getElementById("rapPeriode").value, site=document.getElementById("rapSite").value;
  const surSite=DATA.incidents.filter(i=>!site||i.site===site), inc=surSite.filter(i=>!mois||i.mois===mois);
  const mp=mois?moisPrec(mois):null, incPrec=mp?surSite.filter(i=>i.mois===mp):[];
  const genere=new Date(), genereTxt=`${genere.toLocaleDateString("fr-FR")} à ${genere.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}`;
  const periodeLib=mois?moisLong(mois):`toute la période (${fr(DATA.meta.periode[0])} – ${fr(DATA.meta.periode[1])})`;
  const siteLib=site?lib(site):"Tous";
  const R={mois,site,moisPrec:mp,inc,pannes:inc.filter(estPanne),ind:indicateurs(inc),prec:incPrec.length?indicateurs(incPrec):null,
    parMois:compter(surSite.filter(estPanne),i=>i.mois),anomalies:listeAnomalies(inc),periodeLib,siteLib,genereTxt};
  moisPeriode().forEach(m=>{ R.parMois[m]=R.parMois[m]||0; });
  RAPPORT=R;
  const pied=`<div class="pied-feuille">BaliseIA – Rapport généré le ${genereTxt} – Toute recommandation doit être validée par un expert métier</div>`;
  /* Sauts de page uniquement : après la garde, avant les sections 5, 6 et 7 */
  const feuille=(html)=>`<article class="feuille">${html}${pied}</article>`;
  const sect=(id,html)=>`<section class="sect" id="${id}">${html}</section>`;
  const logo=document.querySelector(".encart .logo");
  /* 2. Indicateurs : colonnes de comparaison seulement s'il existe une période précédente */
  const lignesInd=IND.map(([k,l,f,dec])=>{ const v=[l,`<span data-k="${k}">${R.ind[k]==null?"–":f(R.ind[k])}</span>`];
    return R.prec ? v.concat([R.prec[k]==null?"–":f(R.prec[k]), delta(R.ind[k],R.prec[k],dec)]) : v; });
  const entInd=["Indicateur",esc(maj1(mois?moisLong(mois):"Toute la période"))].concat(R.prec?[esc(maj1(moisLong(mp))),"Écart"]:[]);
  /* 4. Causes et pièces */
  const cau=Object.entries(compter(R.pannes,i=>i.type_panne)).sort((a,b)=>b[1]-a[1]||lib(a[0]).localeCompare(lib(b[0]),"fr"));
  const pie=Object.entries(compter(inc.filter(i=>i.piece_remplacee&&i.piece_remplacee.toLowerCase()!=="aucune"),i=>i.piece_remplacee)).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  const totP=somme(pie.map(x=>x[1]));
  /* 5. Équipements prioritaires : score, MTTR et cause de la Base corrigée (data.json) */
  const top=EQ.filter(e=>!site||e.site===site).slice(0,10);
  /* 6. Anomalies : détail, sauf les incidents non clôturés regroupés en une ligne */
  const ordre=Object.keys(TYPES_ANO);
  const detail=R.anomalies.filter(a=>a.type!=="NON_CLOTURE").sort((a,b)=>ordre.indexOf(a.type)-ordre.indexOf(b.type)||a.i.incident_id.localeCompare(b.i.incident_id));
  const nonClos=R.anomalies.filter(a=>a.type==="NON_CLOTURE").map(a=>a.i).sort((a,b)=>a.incident_id.localeCompare(b.incident_id));
  /* Libellés de traitement abrégés pour le rapport imprimé (détail complet : page Qualité des données) */
  const TRT_COURT={DOUBLON:"Seconde occurrence supprimée",DUREE_MANQUANTE:"Exclue des durées et du MTTR",DUREE_NEGATIVE:"Exclue des durées et du MTTR",
    INCIDENT_LONG:"Conservé, à examiner",INCOHERENCE:"À vérifier par l'expert",NON_CLOTURE:"Compté, exclu du MTTR"};
  const TYPE_COURT={INCOHERENCE:"Incohérence",INCIDENT_LONG:"Incident long"};
  const lignesAno=detail.map(a=>[a.i.incident_id,a.i.equipement_id,TYPE_COURT[a.type]||TYPES_ANO[a.type].lib,esc(a.detail),TRT_COURT[a.type]]);
  if(nonClos.length) lignesAno.push([`<b>${nIncidents(nonClos.length)}</b>`,`${new Set(nonClos.map(i=>i.equipement_id)).size} équipement${new Set(nonClos.map(i=>i.equipement_id)).size>1?"s":""}`,
    "Non clôturé",`<span class="liste-ids">${nonClos.map(i=>i.incident_id).join(", ")}</span>`,TRT_COURT.NON_CLOTURE]);
  /* 7. Recommandations concernées */
  const eqPeriode=new Set(inc.map(i=>i.equipement_id));
  const recs=REC.filter(r=>r.equipement_id ? (!site||r.site===site) && (!mois||eqPeriode.has(r.equipement_id)) : true);

  const garde=`<article class="feuille garde" id="r-garde">
      ${logo?`<img class="logo-r" src="${logo.src}" alt="Logo ASECNA">`:""}
      <div class="surtitre">ATSA-ASECNA Innovation Days 2026 – Groupe G4 UAM</div>
      <h1>Rapport de maintenance du balisage – ${esc(maj1(periodeLib))} – ${siteLib==="Tous"?"Tous les sites":esc(siteLib)}</h1>
      <div class="meta"><span>Période : <b>${esc(maj1(periodeLib))}</b></span><span>Site : <b>${siteLib==="Tous"?"Tous (Dakar, Niamey, Abidjan)":esc(siteLib)}</b></span>
       <span>Date de génération : <b>${genereTxt}</b></span><span>Source : Base BaliseIA et historique des incidents</span></div>
      <div><span class="demo">Données fictives – document de démonstration</span></div>${pied}</article>`;
  const s1=sect("r-synthese",`<h2>1. Synthèse</h2><ol class="constats">${phrasesRapport(R).map(t=>`<li>${t}</li>`).join("")}</ol>
      <p class="src-r">Constats rédigés automatiquement à partir des données de la période (Base BaliseIA, sections 2, 7 et 12).</p>`);
  const s2=sect("r-indicateurs",`<h2>2. Indicateurs</h2>
      ${tableau(entInd,lignesInd,["","num","num","num"],R.prec?["46%","18%","18%","18%"]:["70%","30%"])}
      <p class="src-r">${R.prec?"▲ hausse, ▼ baisse par rapport au mois précédent. ":mois?"Aucune donnée pour le mois précédent. ":`Pas de période précédente : les données commencent le ${fr(DATA.meta.periode[0])}. `}Règles : Base BaliseIA, section 1 ; indicateurs : section 2 ; détail mensuel : sections 7 et 12.</p>`);
  const s3=sect("r-tendance",`<h2>3. Tendance – pannes par mois${site?` (${lib(site)})`:""}${mois?`, ${moisLong(mois)} en évidence`:""}</h2><div class="graphe" id="rGraphMois"></div>
      <p class="src-r">Pannes hors contrôles périodiques. Juin 2026 est incomplet (données jusqu'au ${fr(DATA.meta.periode[1])}). Source : Base BaliseIA, sections 7 et 12.</p>`);
  const s4=sect("r-causes",`<h2>4. Causes de panne et pièces remplacées</h2>
      <div class="deux"><div><h3>Causes de panne (hors contrôles)</h3>${tableau(["Cause","Pannes","Part"],cau.map(([t,n],k)=>[lib(t),`${n} sur ${R.pannes.length}`,barre(n,R.pannes.length,k)]),["","num","num"],["38%","27%","35%"])}</div>
      <div><h3>Pièces remplacées</h3>${tableau(["Pièce","Remplacements","Part"],pie.map(([t,n],k)=>[lib(t),n,barre(n,totP,k)]),["","num","num"],["34%","31%","35%"])}</div></div>
      <p class="src-r">Parts calculées sur les pannes hors contrôles périodiques. « Aucune » n'est pas une pièce. Source : Base BaliseIA, sections 8 et 9.</p>`);
  const s5=sect("r-equipements",`<h2>5. Équipements prioritaires</h2>
      ${tableau(["Rang","Équipement","Site","Criticité","Score","MTTR","Cause principale","Raison"],
        top.map(e=>[e.b.rang,`<b>${e.equipement_id}</b>`,lib(e.site),lib(e.criticite),nf(e.b.score),nf(e.b.mttr)+" h",lib(e.b.cause),texteBase(e.raison)]),
        ["num","nowrap","","","num","num","",""],["6%","17%","9%","8%","7%","8%","13%","32%"])}
      <p class="src-r">Rang, score, MTTR et cause principale : Base BaliseIA corrigée, section 3 (fiches : section 4), mêmes valeurs dans tout l'outil. Score = 40 % pannes + 30 % criticité + 20 % durée + 10 % ancienneté.</p>`);
  const s6=sect("r-anomalies",`<h2>6. Anomalies de données de la période</h2>
      ${tableau(["Incident","Équipement","Type","Détail","Traitement appliqué"],lignesAno,["nowrap","nowrap","","",""],["11%","14%","15%","36%","24%"])}
      <p class="src-r">${R.anomalies.length} anomalie${R.anomalies.length>1?"s":""} au total${nonClos.length?`, dont ${nIncidents(nonClos.length)} non clôturé${nonClos.length>1?"s":""} regroupé${nonClos.length>1?"s":""} sur une ligne`:""}. Source : Base BaliseIA, section 10.</p>`);
  const s7=sect("r-recommandations",`<h2>7. Recommandations</h2>
      <p>Recommandations de la Base BaliseIA (section 11) concernant ${site?`le site de ${lib(site)}`:"les sites"}${mois?" et les équipements ayant eu un incident sur la période":""}, avec leur statut de validation au ${genereTxt}.</p>
      ${recs.map(r=>{ const st=statutTexte(r.id), s=statutRec(r.id);
        return `<div class="rec-r s-${s.ton}" data-rec="${r.id}" data-eq="${r.equipement_id||""}"><header><b>${r.id}</b><span>${r.equipement_id?`${r.equipement_id} · ${lib(r.famille)} · ${lib(r.site)}`:esc(r.titre)+" (transverse)"}</span><span class="st ${st.ton}">${st.txt}</span></header>
          <p class="constat"><b>Constat :</b> ${texteBase(maj1(r.constat))}</p><p><b>Recommandation :</b> ${texteBase(maj1(r.recommandation))}</p></div>`; }).join("")||'<p class="secondaire">Aucune recommandation ne concerne cette sélection.</p>'}
      <p class="src-r">Aucune action n'est déclenchée automatiquement : la décision appartient à l'expert métier.</p>`);
  const s8=sect("r-methode",`<h2>8. Méthode et limites</h2>
      <div class="deux methode-bloc"><div><h3>Règles de calcul (Base BaliseIA, section 1)</h3><ul class="methode">
       <li>Doublon : INC-0046, présent deux fois à l'identique, n'est compté qu'une fois (180 incidents).</li>
       <li>Durée valide : une durée manquante ou négative est exclue des sommes, moyennes et du MTTR ; l'incident reste compté.</li>
       <li>Panne : tout incident hors contrôle périodique.</li>
       <li>MTTR : moyenne des durées valides des incidents clôturés.</li>
       <li>Pièces : « aucune » n'est pas une pièce.</li>
       <li>Score : 40 % pannes + 30 % criticité + 20 % durée + 10 % ancienneté, chaque critère ramené entre 0 et 1 sur les 30 équipements.</li>
       <li>Incident long : plus de 24 h, conservé mais signalé.</li></ul></div>
      <div><h3>Sources</h3><ul class="methode">
       <li>Historique des incidents et interventions (DONNEES_04_BALISAGE_MAINTENANCE.xlsx), recalculé selon ces règles.</li>
       <li>Base BaliseIA corrigée : sections 1, 2, 3, 4, 7, 8, 9, 10, 11 et 12 (corrections listées dans la page Qualité des données).</li>
       <li>Statuts de validation : journal de validation de l'outil BaliseIA.</li></ul>
      <h3>Limites</h3><ul class="methode">
       <li>Données entièrement fictives : document de démonstration.</li>
       <li>Juin 2026 incomplet (données arrêtées au ${fr(DATA.meta.periode[1])}).</li>
       <li>Aucun coût ni stock de pièces dans les données.</li>
       <li>Délai d'intervention constant (3 h) : réactivité non analysable.</li>
       <li>Toute recommandation doit être validée par un expert métier.</li></ul></div></div>`);
  document.getElementById("rapport").innerHTML = garde + feuille(s1+s2+s3+s4) + feuille(s5) + feuille(s6) + feuille(s7+s8);
  barresMois("rGraphMois",moisPeriode().map(m=>({m,v:R.parMois[m]})),mois);
  /* Pied de page imprimé : numérotation gérée par le navigateur (@page) */
  let st=document.getElementById("stylePageRapport");
  if(!st){ st=document.createElement("style"); st.id="stylePageRapport"; document.head.appendChild(st); }
  const piedTxt=`BaliseIA – Rapport généré le ${genereTxt} – page `.replace(/"/g,"'");
  st.textContent=`@media print{@page{size:A4;margin:15mm;
    @bottom-center{content:"${piedTxt}" counter(page) "/" counter(pages) " – Toute recommandation doit être validée par un expert métier";font-family:"Segoe UI",Arial,sans-serif;font-size:8pt;color:#6b7785}}}`;
  document.getElementById("btnImprimer").disabled=false;
}
document.getElementById("btnGenerer").onclick=genererRapport;
document.getElementById("btnImprimer").onclick=()=>window.print();
/* Génère le rapport avec les paramètres affichés s'il ne l'a pas encore été, puis envoie la demande au chat */
document.getElementById("btnCommenter").onclick=()=>{ if(!RAPPORT) genererRapport();
  envoyer(`Rédige un commentaire de synthèse pour le rapport de ${RAPPORT.periodeLib}, site ${RAPPORT.siteLib}, en 5 lignes maximum, avec tes recommandations prioritaires.`); };

/* ====================== Analyses ====================== */
function rendreAnalyses(inc,pannes){
  const parEq=compter(pannes,i=>i.equipement_id);
  barresH("gEquip",Object.entries(parEq).sort((a,b)=>b[1]-a[1]||EQ_DE[b[0]].b.score-EQ_DE[a[0]].b.score).slice(0,10).map(([l,v])=>({l,v})));
  const t=document.getElementById("titreSite");
  if(!SITE){ t.firstChild.textContent="Pannes par site";
    const ps=compter(pannes,i=>i.site);
    barresV("gSite",SITES.map(k=>({l:lib(k),v:ps[k]||0})).sort((a,b)=>b.v-a.v));
  } else { t.firstChild.textContent=`Pannes par famille – ${lib(SITE)}`;
    barresV("gSite",Object.entries(compter(pannes,i=>i.famille)).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([l,v])=>({l:lib(l),v})));
  }
  t.querySelector(".src")?.setAttribute("data-tip",texteSource(SITE?5:6)); t.querySelector(".src")?.setAttribute("aria-label",texteSource(SITE?5:6));
  const pm=compter(pannes,i=>i.mois);
  courbe("gMois",moisPeriode().map(m=>({m,v:pm[m]||0})));
  barresH("gCauses",Object.entries(compter(pannes,i=>i.type_panne)).sort((a,b)=>b[1]-a[1]||lib(a[0]).localeCompare(lib(b[0]),"fr")).map(([k,v])=>({l:lib(k),v})),{G:130});
  barresV("gPieces",Object.entries(compter(inc.filter(i=>i.piece_remplacee && i.piece_remplacee.toLowerCase()!=="aucune"),i=>i.piece_remplacee))
    .sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([k,v])=>({l:lib(k),v})));
}

/* ====================== Équipements ====================== */
function rendreEquipements(){
  const eqs=eqFiltres();
  const t=document.getElementById("titreEquip"); t.firstChild.textContent=`Classement${SITE?` – ${lib(SITE)}`:""} (${eqs.length} équipements)`;
  document.getElementById("hEquip").innerHTML=`<tr><th class="num">Rang global (/30)</th>${SITE?'<th class="num">Rang site</th>':""}<th>Équipement</th><th>Site</th><th>Famille</th><th>Criticité</th><th class="num">Pannes</th><th class="num">Durée (h)</th><th class="num">MTTR (h)</th><th>Cause principale</th><th class="num">Score</th><th>Validation</th></tr>`;
  document.getElementById("tEquip").innerHTML=eqs.map((e,k)=>{
    const crit = estCritique(e) ? `<span class="statut critique" title="Critique : criticité élevée et rang ≤ 5">${lib(e.criticite)}</span>` : lib(e.criticite);
    const rec = REC_EQ[e.equipement_id];
    return `<tr class="clic" data-eq="${e.equipement_id}" tabindex="0"><td class="num">${e.b.rang}</td>${SITE?`<td class="num">${k+1}</td>`:""}
      <td class="nowrap"><b>${e.equipement_id}</b></td><td>${lib(e.site)}</td><td class="nowrap">${lib(e.famille)}</td><td>${crit}</td>
      <td class="num">${e.b.pannes}</td><td class="num">${nf(e.b.duree)}</td><td class="num mttr">${nf(e.b.mttr)}</td>
      <td>${lib(e.b.cause)}</td><td class="num score">${nf(e.b.score)}</td>
      <td>${rec?pastilleRec(rec.id):'<span class="secondaire">–</span>'}</td></tr>`; }).join("");
}

/* Fiche équipement : panneau latéral */
let FICHE=null;
function ouvrirFiche(id){
  const e=EQ_DE[id]; if(!e) return; FICHE=id;
  const incs=DATA.incidents.filter(i=>i.equipement_id===id).sort((a,b)=>b.debut.localeCompare(a.debut));
  const rangSite=EQ.filter(x=>x.site===e.site).findIndex(x=>x.equipement_id===id)+1, nbSite=EQ.filter(x=>x.site===e.site).length;
  const rec=REC_EQ[id], anc=DATA.meta.annee_reference-e.annee_installation;
  const stats=[["Score",`${nf(e.b.score)} / 100`,""],["Rang global",`${e.b.rang} / 30`,""],["Rang site",`${rangSite} / ${nbSite}`,""],
    ["Criticité",lib(e.criticite),estCritique(e)?"critique":""],["Ancienneté",`${anc} ans (${e.annee_installation})`,""],["MTTR",`${nf(e.b.mttr)} h`,""],
    ["Pannes",`${e.b.pannes} sur ${incs.length} incidents`,""],["Durée totale",`${nf(e.b.duree)} h`,""],["Cause principale",lib(e.b.cause),""]];
  const v=document.getElementById("volet");
  v.innerHTML=`<header><div style="flex:1"><h2 id="ficheTitre">${id}</h2><small>${lib(e.famille)} · ${lib(e.site)}, ${secteur(e.localisation)} · installé le ${fr(e.date_installation)}</small></div>
     ${htmlSource("4,3")}<button type="button" class="icone-btn" id="btnFermerFiche" aria-label="Fermer la fiche">${ic("fermer")}</button></header>
   <div class="corps">
    <div class="stats">${stats.map(([l,val,cl])=>`<div class="stat ${cl}"><span>${l}</span><b>${val}</b></div>`).join("")}</div>
    <div><h3>Incidents par mois</h3><div id="frise"></div></div>
    <div><h3>Incidents (${incs.length})</h3>
     <div class="tab" style="max-height:300px"><table class="dt"><thead><tr><th>Date</th><th>Type</th><th class="num">Durée</th><th>Statut</th><th>Pièce</th></tr></thead><tbody>
     ${incs.map(i=>`<tr><td class="nowrap"><span class="ref">${i.incident_id}</span><br><span class="secondaire">${frDH(i.debut)}</span></td><td>${lib(i.type_panne)}</td>
       <td class="num nowrap">${estValide(i)?nf(i.duree)+" h":'<span class="secondaire">non valide</span>'}</td>
       <td>${i.statut==="EN_COURS"?'<span class="statut critique">En cours</span>':'<span class="statut neutre">Clôturé</span>'}</td><td>${lib(i.piece_remplacee)}</td></tr>`).join("")}
     </tbody></table></div></div>
    <div><h3>Recommandation liée</h3>${rec?`<div class="lie"><div class="ligne"><span class="rec-id">${rec.id}</span>${pastilleRec(rec.id)}</div>
      <div>${actionCourte(rec)}.</div><div><button type="button" class="btn petit" data-examiner="${rec.id}">Examiner la recommandation ${ic("fleche")}</button></div></div>`
      : '<div class="lie secondaire">Aucune recommandation documentée pour cet équipement.</div>'}</div>
    <div><button type="button" class="btn prim" id="btnFicheChat">${ic("message")}Demander à BaliseIA</button></div>
   </div>`;
  /* Mini-frise : incidents par mois sur la période */
  const parMois=compter(incs,i=>i.mois), mois=moisPeriode(), W=500, H=74, bw=W/mois.length, max=Math.max(1,...Object.values(parMois));
  const s=svg(W,H,"Incidents par mois");
  mois.forEach((m,k)=>{ const n=parMois[m]||0, h=n?8+(H-30)*n/max:2;
    const r=el(s,"rect",{x:k*bw+2,y:H-18-h,width:bw-4,height:h,rx:2,fill:n?C.bleu:"#dfe5eb"}); bulle(r,`${moisCourt(m)} : ${n} incident${n>1?"s":""}`);
    if(n) el(s,"text",{x:k*bw+bw/2,y:H-22-h,"text-anchor":"middle","font-size":10,fill:"#0d2f55"},n);
    if(k%3===0||k===mois.length-1) el(s,"text",{x:k*bw+bw/2,y:H-4,"text-anchor":"middle","font-size":9.5,fill:"#6b7785"},`${m.slice(5)}/${m.slice(2,4)}`); });
  v.querySelector("#frise").appendChild(s);
  v.querySelector("#btnFermerFiche").onclick=fermerFiche;
  v.querySelector("#btnFicheChat").onclick=()=>envoyer(`Explique-moi la situation de ${id}.`);
  document.querySelectorAll("#tEquip tr").forEach(tr=>tr.classList.toggle("sel",tr.dataset.eq===id));
  v.classList.add("ouvert"); document.getElementById("voile").classList.add("ouvert");
  v.querySelector("#btnFermerFiche").focus();
}
function fermerFiche(){ FICHE=null; document.getElementById("volet").classList.remove("ouvert"); document.getElementById("voile").classList.remove("ouvert");
  document.querySelectorAll("#tEquip tr.sel").forEach(tr=>tr.classList.remove("sel")); }
document.getElementById("voile").onclick=fermerFiche;
document.getElementById("tEquip").addEventListener("click",ev=>{ const tr=ev.target.closest("tr[data-eq]"); if(tr) ouvrirFiche(tr.dataset.eq); });
document.getElementById("tEquip").addEventListener("keydown",ev=>{ const tr=ev.target.closest("tr[data-eq]"); if(tr && (ev.key==="Enter"||ev.key===" ")){ ev.preventDefault(); ouvrirFiche(tr.dataset.eq); } });
document.addEventListener("keydown",ev=>{ if(ev.key==="Escape"){ fermerFiche(); document.getElementById("chat").classList.remove("ouvert"); } });
/* Boutons « Examiner » : page Recommandations sur la bonne fiche */
document.addEventListener("click",ev=>{ const b=ev.target.closest("[data-examiner]"); if(b){ fermerFiche(); location.hash="#recommandations/"+b.dataset.examiner; } });

/* ====================== Qualité ====================== */
function rendreQualite(inc){
  const anos=listeAnomalies(inc), nb=compter(anos,a=>a.type), ordre=Object.keys(TYPES_ANO);
  document.getElementById("chipsQualite").innerHTML=ordre.filter(t=>nb[t])
    .map(t=>`<div class="chip ${TYPES_ANO[t].ton}"><b>${nb[t]}</b>${TYPES_ANO[t].lib}</div>`).join("");
  document.getElementById("titreQualite").firstChild.textContent=`Anomalies détectées${SITE?` – ${lib(SITE)}`:""} (${anos.length})`;
  document.getElementById("tQualite").innerHTML=anos.slice().sort((a,b)=>ordre.indexOf(a.type)-ordre.indexOf(b.type)||a.i.incident_id.localeCompare(b.i.incident_id))
    .map(a=>{ const T=TYPES_ANO[a.type];
      return `<tr><td class="nowrap"><span class="ref">${a.i.incident_id}</span></td><td class="nowrap">${a.i.equipement_id}</td><td>${lib(a.i.site)}</td>
      <td class="nowrap"><span class="statut ${T.ton||"neutre"}">${T.lib}</span></td><td>${esc(a.detail)}</td><td class="secondaire">${T.trt}</td></tr>`; }).join("");
  const siteDe = el => el.startsWith("EQ-") ? EQ_DE[el].site : (REC_DE[el]||{}).site;
  const val = (champ,v) => typeof v==="number" ? nf(v) : champ==="Cause principale" ? lib(v) : texteBase(String(v));
  const ecarts=DATA.ecarts_base.filter(x=>!SITE||!siteDe(x.element)||siteDe(x.element)===SITE);
  document.getElementById("carteEcarts").hidden=!ecarts.length;
  document.getElementById("tEcarts").innerHTML=ecarts.map(x=>`<tr><td class="nowrap">${x.element.startsWith("REC")?`<span class="rec-id">${x.element}</span>`:x.element}</td>
    <td>${esc(x.champ)}</td><td>${val(x.champ,x.base)}</td><td><b>${val(x.champ,x.autre)}</b></td><td class="secondaire">${esc(x.traitement)}</td></tr>`).join("");
}

/* ====================== Rendu global ====================== */
function rendre(tout=true){
  const inc=incFiltres(), pannes=inc.filter(estPanne), valides=inc.filter(estValide);
  const enCours=inc.filter(i=>i.statut==="EN_COURS").length;
  document.getElementById("contexte").textContent=`Prototype Innovation Days 2026 · ${fr(DATA.meta.periode[0])} – ${fr(DATA.meta.periode[1])} · ${eqFiltres().length} équipements suivis`;
  rendreResume(inc,pannes,valides,enCours);
  rendreEquipements();
  if(tout){ rendreAnalyses(inc,pannes); rendreQualite(inc); rendreRecommandations(); }
  if(FICHE) ouvrirFiche(FICHE);
}
document.getElementById("filtre").addEventListener("click",ev=>{
  const b=ev.target.closest("button[data-site]"); if(!b) return;
  SITE=b.dataset.site;
  document.querySelectorAll("#filtre button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));
  fermerFiche(); rendre();
});

/* ====================== Navigation par onglets (hash) ====================== */
const VUES=["resume","recommandations","rapports","analyses","equipements","qualite","assistant"];
function naviguer(){
  const [nom,cible]=location.hash.slice(1).split("/"), v=VUES.includes(nom)?nom:"resume";
  VUES.forEach(x=>document.getElementById("v-"+x).classList.toggle("visible",x===v));
  document.querySelectorAll("#nav a").forEach(a=>a.classList.toggle("actif",a.dataset.vue===v));
  const chat=document.getElementById("chat"), assistant=v==="assistant";
  chat.classList.toggle("pleine",assistant); chat.classList.toggle("tiroir",!assistant);
  chat.classList.remove("ouvert");   // changer de page referme le panneau (la conversation est conservée)
  document.getElementById("fab").hidden=assistant;
  document.body.classList.toggle("sur-assistant",assistant);
  document.body.dataset.vue=v;   // l'impression du rapport n'est active que sur la page Rapports
  fermerFiche();
  const carte=cible && document.getElementById("rec-"+cible);
  if(v==="recommandations" && carte && !OUVERTES.has(cible)){ OUVERTES.add(cible); carte.classList.add("form-ouvert"); }
  if(v==="recommandations" && carte){
    requestAnimationFrame(()=>{ carte.scrollIntoView({block:"start"}); carte.classList.add("flash"); setTimeout(()=>carte.classList.remove("flash"),1800);
      carte.querySelector("input[name=nom]")?.focus({preventScroll:true}); });
  } else window.scrollTo(0,0);
}
window.addEventListener("hashchange",naviguer);

/* ====================== Chat BaliseIA ====================== */
const estUrl = u => /^https?:\/\//i.test((u||"").trim());
const secretValide = s => !!s && !/COLLER ICI|^__DIRECTLINE/i.test(s) && s.trim().length >= 20;
const secretActif = () => [lire(CLE_SECRET),DIRECTLINE_SECRET].find(secretValide)?.trim() || "";
const iframeActive = () => lire(CLE_AGENT) || COPILOT_URL;
let chatStore=null, chatMode=null, minuteur=null, fileAttente=[];

function chargerScript(src){
  return new Promise((ok,ko)=>{ if(window.WebChat) return ok();
    const s=document.createElement("script"); s.src=src; s.crossOrigin="anonymous";
    s.onload=ok; s.onerror=()=>ko(new Error("Chargement de Web Chat impossible")); document.head.appendChild(s); });
}
/* Indicateur « BaliseIA analyse les données… » : masqué uniquement à la réception d'un message du bot */
/* Indicateur « BaliseIA analyse les données… »
   - affiché dès l'envoi d'une question ;
   - les activités « typing » et les messages de progression (streamType informative / streaming)
     de Copilot Studio le maintiennent ;
   - masqué uniquement après un message final du bot, suivi de DELAI_FIN_TOUR_MS sans nouvelle activité
     (Copilot Studio envoie souvent plusieurs messages pour une même réponse) ;
   - au-delà de DELAI_MAX_REPONSE_MS, le texte change mais l'animation continue jusqu'à la réponse. */
const DELAI_FIN_TOUR_MS = 1500;
let enAttente=false, finTour=null;
function attente(actif){
  const a=document.getElementById("attente"), t=document.getElementById("attenteTxt");
  clearTimeout(minuteur); clearTimeout(finTour); enAttente=actif;
  if(!actif){ a.classList.remove("visible","lent"); return; }
  a.classList.add("visible"); a.classList.remove("lent"); t.textContent="BaliseIA analyse les données…";
  minuteur=setTimeout(()=>{ a.classList.add("lent"); t.textContent="La réponse prend plus de temps que prévu, réessayez."; },DELAI_MAX_REPONSE_MS);
}
const estProgression = a => a.type==="typing" || ["informative","streaming"].includes(a.channelData?.streamType);
const estReponseFinale = a => a.type==="message" && !estProgression(a) && (a.text || (a.attachments||[]).length || a.suggestedActions);
const middleware = () => next => action => {
  if(action.type==="DIRECT_LINE/POST_ACTIVITY" && action.payload?.activity?.type==="message") attente(true);
  else if(action.type==="DIRECT_LINE/INCOMING_ACTIVITY" && enAttente){
    const a=action.payload?.activity;
    if(a?.from && a.from.role!=="user"){   // activité de l'agent (l'écho de nos propres messages a le rôle « user »)
      if(estProgression(a)) clearTimeout(finTour);                       // le bot travaille encore
      else if(estReponseFinale(a)){ clearTimeout(finTour); finTour=setTimeout(()=>attente(false),DELAI_FIN_TOUR_MS); }
    }
  }
  return next(action);
};
/* Mise en page « ChatGPT » : réponses de l'agent sans bulle, questions de l'utilisateur en bulle claire à droite */
const STYLE = {
  primaryFont:"'Segoe UI', Tahoma, Arial, sans-serif", backgroundColor:"#ffffff",
  bubbleBackground:"transparent", bubbleBorderWidth:0, bubbleBorderRadius:0, bubbleNubSize:0,
  bubbleFromUserBackground:"#eef3f8", bubbleFromUserTextColor:"#1c2733", bubbleFromUserBorderWidth:0,
  bubbleFromUserBorderRadius:18, bubbleFromUserNubSize:0,
  bubbleMaxWidth:860, bubbleMinWidth:0,
  botAvatarInitials:"", userAvatarInitials:"",      // pas d'avatar
  hideUploadButton:true, sendBoxBackground:"#ffffff", sendBoxButtonColor:"#0b4f8a", sendBoxHeight:48,
  typingAnimationDuration:120000
};
/* Une tentative de connexion Direct Line (secret) sur un domaine : Web Chat ouvre la connexion,
   la page suit connectionStatus$ (2 = en ligne ; 3, 4, 5 = jeton expiré, échec, fin). */
let basculeDirectLine=false;   // vrai pendant l'abandon d'une connexion en échec
const ID_UTILISATEUR = "baliseia_" + Math.random().toString(36).slice(2, 10);   // identifiant de l'utilisateur pour cette session
function connexionDirectLine(secret, domaine){
  return new Promise((resoudre, rejeter)=>{
    const directLine = window.WebChat.createDirectLine(domaine ? { secret, domain:domaine } : { secret });
    const store = window.WebChat.createStore({}, middleware);
    window.WebChat.renderWebChat({ directLine, store, userID:ID_UTILISATEUR, locale:"fr-FR", styleOptions:STYLE }, document.getElementById("webchat"));
    let fini=false, abo=null;
    const fin = err => { if(fini) return; fini=true; clearTimeout(tempo); abo && abo.unsubscribe();
      if(err){ basculeDirectLine=true; try{ directLine.end(); }catch(e){} setTimeout(()=>{ basculeDirectLine=false; }, 3000); rejeter(err); }
      else resoudre({ directLine, store }); };
    const tempo = setTimeout(()=>fin(new Error("délai de connexion dépassé")), DELAI_CONNEXION_MS);
    abo = directLine.connectionStatus$.subscribe({
      next(statut){
        if(statut===2){   // en ligne : startConversation déclenche le message d'accueil de l'agent
          /* Direct Line (secret) exige un expéditeur : même identifiant que celui de Web Chat */
          directLine.postActivity({ type:"event", name:"startConversation", locale:"fr-FR", from:{ id:ID_UTILISATEUR, role:"user" } })
            .subscribe({ error(e){ console.info("BaliseIA – startConversation refusé :", e && e.message); } });
          fin(null);
        } else if(statut===3 || statut===4 || statut===5) fin(new Error(`statut Direct Line ${statut}`));
      },
      error(e){ fin(e); } });
  });
}
/* Erreurs internes de Web Chat levées par une connexion abandonnée : attendues, non affichées */
window.addEventListener("error", e=>{ if(basculeDirectLine){ e.preventDefault(); console.info("BaliseIA – erreur ignorée pendant la bascule Direct Line :", e.message); } });
window.addEventListener("unhandledrejection", e=>{ if(basculeDirectLine){ e.preventDefault(); console.info("BaliseIA – rejet ignoré pendant la bascule Direct Line"); } });
/* Indicateur de connexion de l'en-tête du chat */
function etatChat(etat){
  const b=document.getElementById("etatChat"), LIB={"en-ligne":"En ligne",iframe:"Mode iframe",connexion:"Connexion…"};
  b.className="etat-"+etat; b.textContent=`BaliseIA – ${LIB[etat]}`; b.title=etat==="iframe"?"Chat de repli Copilot Studio (mise en forme limitée)":"";
}
async function initChat(){
  etatChat("connexion");
  const secret=secretActif();
  if(!secret) return modeIframe("aucun secret Direct Line configuré");
  try{ await chargerScript(WEBCHAT_JS); } catch(e){ return modeIframe(e.message); }
  for(const domaine of DOMAINES_DIRECTLINE){
    try{
      const { store } = await connexionDirectLine(secret, domaine);
      chatStore=store; chatMode="webchat"; etatChat("en-ligne");
      console.info("BaliseIA – Direct Line connecté :", domaine || "domaine par défaut");
      surveillerIdentifiants();
      fileAttente.splice(0).forEach(q=>envoyer(q));
      return;
    } catch(e){ console.info("BaliseIA – échec Direct Line :", domaine || "domaine par défaut", "–", e.message); }
  }
  modeIframe("connexion Direct Line impossible");
}
function modeIframe(raison){
  console.info("BaliseIA – mode iframe (mise en forme limitée) :", raison||"repli");
  etatChat("iframe");
  chatMode="iframe"; chatStore=null;
  const f=document.createElement("iframe");
  f.src=iframeActive(); f.title="BaliseIA – Agent Copilot Studio"; f.id="iframeAgent";
  f.setAttribute("allow","clipboard-write; microphone");
  const cadre=document.createElement("div"); cadre.className="chat-frame"; cadre.appendChild(f);
  const w=document.getElementById("webchat"); w.innerHTML=""; w.appendChild(cadre);
  fileAttente.splice(0).forEach(q=>copier(q));
}
/* Identifiants EQ-… / INC-… jamais coupés dans les réponses Markdown */
function surveillerIdentifiants(){
  if(surveillerIdentifiants.actif) return; surveillerIdentifiants.actif=true;
  const RX=/\b(?:EQ|INC|INT|TECH|REC)-[A-Z0-9-]*[0-9A-Z]/g, zone=document.getElementById("webchat");
  let prevu=false;
  const traiter=()=>{ prevu=false;
    zone.querySelectorAll(".webchat__render-markdown").forEach(md=>{
      const w=document.createTreeWalker(md,NodeFilter.SHOW_TEXT), cibles=[];
      while(w.nextNode()){ const n=w.currentNode; RX.lastIndex=0;
        if(RX.test(n.nodeValue) && !n.parentElement.closest(".id-nowrap")) cibles.push(n); }
      cibles.forEach(n=>{ const frag=document.createDocumentFragment(); let dernier=0; const t=n.nodeValue;
        t.replace(RX,(m,pos)=>{ frag.appendChild(document.createTextNode(t.slice(dernier,pos)));
          const s=document.createElement("span"); s.className="id-nowrap"; s.textContent=m; frag.appendChild(s); dernier=pos+m.length; return m; });
        frag.appendChild(document.createTextNode(t.slice(dernier))); n.parentNode.replaceChild(frag,n); });
    }); };
  new MutationObserver(()=>{ if(!prevu){ prevu=true; requestAnimationFrame(traiter); } }).observe(zone,{childList:true,subtree:true});
}
function toast(t){ const e=document.getElementById("toast"); e.textContent=t; clearTimeout(toast.t); toast.t=setTimeout(()=>e.textContent="",5000); }
function copier(t){
  const box=document.getElementById("aColler");
  document.getElementById("aCollerTexte").textContent=t; box.hidden=false;
  const ok=()=>toast("Question copiée dans le presse-papiers.");
  const repli=()=>{ const ta=document.createElement("textarea"); ta.value=t; document.body.appendChild(ta); ta.select(); try{document.execCommand("copy");}catch(e){} ta.remove(); ok(); };
  if(navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(ok,repli); else repli();
}
function ouvrirChat(){ fermerFiche(); if(!document.getElementById("chat").classList.contains("pleine")) document.getElementById("chat").classList.add("ouvert"); }
/* Envoie la question au chat et ouvre le panneau (copie en mode iframe) */
function envoyer(q){
  ouvrirChat();
  if(chatMode==="webchat" && chatStore) chatStore.dispatch({ type:"WEB_CHAT/SEND_MESSAGE", payload:{ text:q } });
  else if(chatMode==="iframe") copier(q);
  else fileAttente.push(q);
}
const QUESTIONS=["Quels équipements traiter en priorité ?","Pourquoi EQ-DAK-SIM-06 est-il en tête ?",
  "Quelle est la cause principale de EQ-DAK-SIM-08 ?","Nouvelle panne de connectique sur EQ-DAK-SIM-06 : que dois-je préparer ?",
  "Fais la synthèse de décembre 2025.","Quelles anomalies as-tu trouvées ?"];
QUESTIONS.forEach(q=>{ const b=document.createElement("button"); b.type="button"; b.textContent=q; b.onclick=()=>envoyer(q); document.getElementById("lQuestions").appendChild(b); });

document.getElementById("btnFermerColler").onclick=()=>{ document.getElementById("aColler").hidden=true; };
document.getElementById("btnRecopier").onclick=()=>copier(document.getElementById("aCollerTexte").textContent);
document.getElementById("fab").onclick=()=>document.getElementById("chat").classList.toggle("ouvert");
document.getElementById("btnFermer").onclick=()=>document.getElementById("chat").classList.remove("ouvert");
function extraireUrl(txt){ txt=(txt||"").trim(); const m=txt.match(/src\s*=\s*["']([^"']+)["']/i); const u=(m?m[1]:txt).replace(/&amp;/g,"&"); return estUrl(u)?u:""; }
const msgConfig=t=>document.getElementById("msgConfig").textContent=t;
document.getElementById("btnConfig").onclick=()=>{
  document.getElementById("config").classList.toggle("ouvert");
  document.getElementById("champSecret").value="";
  document.getElementById("champSecret").placeholder = secretActif() ? "Secret enregistré (laisser vide pour le conserver)" : "Secret 1 du canal Direct Line de l'agent";
  document.getElementById("champIframe").value=iframeActive();
};
document.getElementById("btnConnecter").onclick=()=>{
  const sec=document.getElementById("champSecret").value.trim(), ifr=extraireUrl(document.getElementById("champIframe").value);
  if(sec && !secretValide(sec)) return msgConfig("Secret Direct Line invalide.");
  if(sec) ecrire(CLE_SECRET, sec===DIRECTLINE_SECRET ? "" : sec);
  ecrire(CLE_AGENT, ifr===COPILOT_URL ? "" : ifr);
  location.reload();   // une seule conversation : on recharge plutôt que d'en ouvrir une seconde
};
document.getElementById("btnOnglet").onclick=()=>window.open(extraireUrl(document.getElementById("champIframe").value)||iframeActive(),"_blank","noopener");
document.getElementById("btnDefaut").onclick=()=>{ ecrire(CLE_SECRET,""); ecrire(CLE_AGENT,""); location.reload(); };

/* Hauteur réelle du bandeau (il passe sur deux lignes sur écran étroit) : place le chat 16 px dessous */
const bandeau=document.querySelector(".bandeau");
const majBandeau=()=>document.documentElement.style.setProperty("--hb",Math.ceil(bandeau.getBoundingClientRect().height)+"px");
new ResizeObserver(majBandeau).observe(bandeau); majBandeau();

/* ====================== Démarrage ====================== */
poserIcones(); poserSources();
rendre();
naviguer();
initChat();
</script>
</body>
</html>
"""


def main(partage=False):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    # « </ » échappé pour qu'aucune chaîne ne puisse fermer la balise <script>
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    logo = (f'<img class="logo" src="data:image/png;base64,{base64.b64encode(LOGO.read_bytes()).decode()}" alt="Logo ASECNA">'
            if LOGO.exists() else "")
    # Version de partage : le secret n'est jamais lu, le chat utilise l'iframe Copilot Studio
    secret = "" if partage else (SECRET.read_text(encoding="utf-8").strip() if SECRET.exists() else "")
    sortie = SORTIE_PARTAGE if partage else SORTIE
    marqueur = 'const DIRECTLINE_SECRET = "__DIRECTLINE_SECRET__";'
    assert GABARIT.count(marqueur) == 1
    page = GABARIT.replace("__LOGO__", logo).replace(marqueur, f'const DIRECTLINE_SECRET = "{(secret or SECRET_A_COLLER).replace(chr(34), "")}";')
    page = page.replace("__DATA__", js)
    if partage and SECRET.exists():   # garde-fou : le secret ne doit apparaître nulle part dans la version partagée
        assert SECRET.read_text(encoding="utf-8").strip() not in page, "secret détecté dans la version de partage"
    sortie.write_text(page, encoding="utf-8")
    if secret:
        print("Secret Direct Line injecté depuis directline_secret.txt – ne pas publier ni versionner le HTML généré.")
    if partage:
        print("Version de partage SANS secret : le chat passe par l'iframe Copilot Studio.")
    print(f"{sortie.name} généré ({sortie.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main(partage="--partage" in sys.argv)
