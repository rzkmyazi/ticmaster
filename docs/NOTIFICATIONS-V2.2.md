# Notifications V2.2 — correctif XSS et refonte du panneau

**TIC MASTER #by_Myazirzk** — 30 octobre 2026

> Défaut signalé : « Dans le panneau des notifications, certains messages affichent
> directement du code HTML/JavaScript, ex. `&lt;script&gt;alert('xss')&lt;/script&gt;`
> — cas constaté : *Nouvelle annonce : Test XSS auto / Description :
> `<script>alert('xss')</script>`*. Ce comportement n'est pas acceptable pour une
> plateforme professionnelle. »

---

## 1. Diagnostic (avant toute modification)

| Constat | Détail |
|---|---|
| Origine du texte | `admin.announcements` envoyait `body[:160]` **brut** à `notify_many()`, sans nettoyage. |
| Origine secondaire | Les corps de messages privés (`social.api_send_message`) étaient également transmis bruts. |
| Base locale | 176 notifications sur 239 contenaient du balisage (`<script>`, `<b>`…). |
| Pourquoi ce n'était pas exécuté | Jinja échappe le rendu serveur et `app.js` écrit via `textContent` : le code **s'affichait** au lieu de s'exécuter. Le défaut est donc d'**affichage**, pas d'exécution — mais il reste inacceptable. |
| Conséquence | Le balisage polluait aussi l'historique, les bannières et l'API JSON. |

## 2. Correctif — le texte est nettoyé à la source

### `app/text_safety.py` (nouveau, 1 point de passage)

| Fonction | Rôle |
|---|---|
| `clean_text(raw, limit, fallback)` | décode les entités (jusqu'à 3 tours : `&amp;lt;script&amp;gt;`), retire `<script>/<style>/<iframe>…`, toutes les balises, les commentaires, les caractères invisibles (U+200B…), les schémas `javascript:`/`data:`, normalise les espaces et coupe au mot. Dernier filet : plus aucun `<` ni `>` ne sort. |
| `clean_title(raw, limit)` | même nettoyage, une seule ligne, coupe à 120 caractères. |
| `looks_like_markup(raw)` | détecte un contenu qui n'était que du code. |
| `preview(raw)` | aperçu court pour les listes. |

Si le contenu ne contenait **que** du code, la notification affiche
« Contenu retiré : cette notification ne contenait pas de texte lisible. »
plutôt qu'une ligne vide.

### Points d'application

| Endroit | Traitement |
|---|---|
| `notify()` / `notify_many()` / `notify_staff()` | titre et corps nettoyés **avant** l'enregistrement. |
| `Notification.title_clean` / `body_clean` | nettoyage **à l'affichage** : les anciennes lignes restent sûres, même non migrées. |
| `as_dict()` (API JSON) | textes nettoyés, URL interne uniquement (`safe_url`). |
| `admin.announcements` (création + modification) | `_texte_annonce()` : le texte normal passe tel quel ; si du balisage est détecté, il est retiré. Une annonce faite **uniquement** de code est refusée avec un message explicite. |
| Réparation au démarrage | `sanitize_rows()` : 176 lignes assainies automatiquement chez moi, sans supprimer aucune ligne. |

## 3. Refonte du panneau

| Élément | Mise en œuvre |
|---|---|
| Titre clair | `notif-title`, 2 lignes maximum, gras, texte propre. |
| Message lisible | `notif-body`, 2 lignes, `textContent` uniquement côté JS. |
| Date et heure | `Aujourd'hui · 11:13`, `Hier · 09:40`, sinon `28/10/2026 · 18:02` (fuseau `TZ_OFFSET`). |
| Icône par type | message, battle, annonce, note, compte, système — couleur dédiée. |
| Indicateur non lue | fond `accent-soft` + point rouge + compteur sur la cloche. |
| Tout marquer comme lu | bouton dans l'entête, masqué quand tout est lu ; renvoie `count` pour synchroniser. |
| Voir tout l'historique | lien pied de panneau + lien « historique » dans l'entête. |
| Suppression individuelle | corbeille par ligne → `DELETE /api/notifications/<id>` (CSRF + propriété) ; repli sans JavaScript : formulaire POST. |
| État vide | pastille + « Tout est à jour » + explication. |
| Rafraîchissement | AJAX toutes les 25 s, en pause si l'onglet est masqué, immédiat à l'ouverture et au retour sur l'onglet — **jamais** de rechargement de page. |
| Compteur synchronisé | badge de la cloche, sous-titre du panneau et compteur du menu latéral suivent tous la réponse du serveur. |

Le panneau ne marque plus **tout lu automatiquement** à l'ouverture : les non-lues
restent visibles, et c'est le bouton qui agit — comportement attendu sur une
plateforme professionnelle.

## 4. Gestion intelligente (pas de doublons)

| Règle | Détail |
|---|---|
| `dedupe_key` (nouvelle colonne) | identifie l'événement : `annonce:42`, `message:318`, `battle-join:12:5`, `note:attempt:77`… |
| Annonce | une annonce = **une** notification par personne, même si le service est rappelé (re-publication, correctif, double clic). |
| Messages | clé = identifiant du message : deux « Salut » restent deux notifications, un même message ne se dédouble jamais. |
| Doublon automatique | sans clé explicite, deux titres identiques dans les 12 h ne produisent qu'une notification. |
| Événements répétables | `dedupe_hours=0` : redémarrage de battle, réinitialisation de mot de passe… notifient à chaque fois. |
| Soi-même | aucune notification pour l'auteur de l'action. |
| Annonce supprimée | ses notifications sont retirées (plus de lien mort). |
| Doublons historiques | bouton « Fusionner les doublons » dans `/admin/parametres` (super administrateur, CSRF, journalisé) : garde la plus récente de chaque groupe identique. Annonces par défaut ; autres types sur demande. |
| Outil en ligne de commande | `tools/repair_notifications.py` — simulation par défaut, `--apply` pour écrire. |

## 5. Sécurité

- Toute route de modification/suppression vérifie **`user_id = utilisateur connecté`** via `get_owned()` ; sinon **404** (aucune fuite d'existence).
- CSRF obligatoire (`X-CSRF-Token` ou champ `csrf_token`) sur DELETE et POST.
- `safe_url()` : seuls les chemins internes sont acceptés (pas de redirection ouverte).
- Aucun HTML construit côté navigateur : `textContent` / `createElement` exclusivement.
- Suppression individuelle tracée par la réponse `{ok, deleted, count}` (pas de révocation de session, pas d'effet de bord).

## 6. Tests exécutés (résultats mesurés)

| Commande | Résultat |
|---|---|
| `pytest -q` | **141 réussis** (114 existants + 27 nouveaux), 0 échec |
| `tools/verify.py` (local) | **278 contrôles conformes**, 0 échec |
| `tools/test_sessions.py` (local) | **31/31** |
| Scénario navigateur Android 412×915 | annonce `<script>alert('xss')</script>` → texte propre, 0 balise, 0 erreur JavaScript |
| Scénario thème clair + ordinateur 1366×800 | rendu vérifié (captures ci-dessous) |
| Fusion des doublons (local) | 176 copies d'annonces fusionnées, 1 copie conservée par personne |

Nouveaux tests (`tests/test_notifications.py`) :

1. balisage jamais affiché (6 variantes : direct, entités, double encodage, attributs, iframe, style) ;
2. texte utile conservé, balises retirées ;
3. notification stockée propre, corps « Contenu retiré » ;
4. API JSON sans `<` ni `>` ;
5. page d'historique sans `<script>` ;
6. `sanitize_rows()` répare l'existant ;
7. même annonce → une seule notification ;
8. `notify_many` ne double pas les destinataires ;
9. doublon automatique par titre + `dedupe_hours=0` ;
10. pas de notification à soi-même ;
11. lire/supprimer la notification d'un autre → 404 ;
12. suppression de sa notification → 200 + compteur ;
13. suppression par formulaire sans JavaScript ;
14. CSRF obligatoire ;
15. anonyme → redirection ;
16. compteur synchronisé ;
17. statistiques de doublons ;
18. fusion réservée au super administrateur ;
19. fusion conserve une seule copie ;
20. page `/admin/parametres` affiche l'état.

## 7. Captures (Android 412×915, production locale)

| Fichier | Contenu |
|---|---|
| `apercus/android/v22-panneau.png` | panneau, thème sombre, annonce nettoyée |
| `apercus/android/v22-tout-lu.png` | après « Tout marquer comme lu » |
| `apercus/android/v22-historique.png` | page d'historique, filtres et corbeilles |
| `apercus/android/v22-panneau-clair.png` | thème clair |
| `apercus/android/v22-panneau-ordinateur.png` | ordinateur 1366×800 |
| `apercus/android/v22-admin-notifications.png` | carte « Notifications » dans les paramètres |

## 8. Compatibilité

- Aucune fonctionnalité retirée : messages, battles, annonces, notes, comptes, historique, filtres et purge des lues sont conservés.
- Une seule colonne ajoutée (`notifications.dedupe_key`), créée automatiquement au démarrage par `ensure_schema()` — compatible SQLite (PythonAnywhere) et PostgreSQL (Render).
- Sauvegarde de la base effectuée avant migration (`backup-avant-v22-20261030-0807.db` en local).
- Aucun compte, rôle ou identifiant modifié.
