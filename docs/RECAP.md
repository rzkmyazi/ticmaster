# TIC MASTER — récapitulatif des demandes #by_Myazirzk

Dernière mise à jour : **29/10/2026** — état vérifié en production.

| Application | Adresse |
|---|---|
| **Render (principale)** | <https://ticmaster.onrender.com> |
| **PythonAnywhere** | <https://myazirzk1.pythonanywhere.com> |
| **Code source** | <https://github.com/rzkmyazi/ticmaster> |

Identifiants super administrateur : **Myazirzk** / `Fiaram131213!!`
(le compte est créé par l'administration ; **aucune inscription publique** n'existe).

---

## 1. Le super Admin peut modifier les cours et les modules — ✔

| Où | Chemin |
|---|---|
| Menu | **Administration → Modules & leçons** |
| Modifier un module | `/admin/modules` → crayon ✏️ → titre, résumé, description, image, niveau, statut, ordre, catégorie |
| Modifier une leçon | `/admin/modules/<id>/modifier` → section « Leçons » → crayon ✏️ (titre, contenu, image, vidéo, document, durée, publication) |
| Créer | boutons « Nouveau module » et « Ajouter une leçon » |

Le super administrateur a **tous les droits** : modules, leçons, ressources, exercices, questions,
annonces, examens. Les permissions sont vérifiées côté serveur (un élève reçoit **403**).

---

## 2. Conservation des données illimitée — ✔

**Paramètres → onglet Général → Conservation des données**

- Valeur **`0` = conservation illimitée** (réglage par défaut) : aucune donnée n'est jamais supprimée automatiquement.
- Laisser vide, écrire `0` ou `illimite` produit le même résultat.
- Une valeur positive n'est qu'une durée indicative pour la politique RGPD.

---

## 3. Statistiques individuelles de chaque élève, note /20 — ✔

| Écran | Chemin | Contenu |
|---|---|---|
| Tableau de bord | `/admin/` → « Notes individuelles (sur 20) » | rang, note /20, mention, exercices et examens /20, progression |
| Notes des élèves | `/admin/notes` | relevé complet, tri par moyenne / numéro / groupe, export CSV |
| Bulletin individuel | `/admin/notes/<élève>` | note /20, mention, rang, résultats par module et par trimestre, historique |
| Statistiques de la classe | `/admin/statistiques` | moyenne, médiane, distribution des mentions, palmarès, élèves à soutenir |

---

## 4. Seuls le super admin et l'administrateur acceptent les battles — ✔

| Étape | Comportement |
|---|---|
| Un élève crée une battle (solo ou groupe) | statut **`pending`** — rien ne démarre |
| Tentative de démarrage avant accord | **403** « doit d'abord être acceptée par l'administration » |
| Le personnel ouvre **Administration → Battles à valider** (`/admin/battles`) | Accepter → salon ouvert · Refuser → statut `refused` |
| Un élève sur cette page | **403** (page et actions) |

---

## 5. Réseau social dans le profil — ✔

**Mon profil → onglet « Fil d'actualité »** (`/mon-profil`)

- **Publier** un message, une photo, ou les deux (PNG, JPG, GIF, WEBP — 30 Mo max).
- **Réagir** avec les cinq emojis : ❤️ J'aime · 😂 Rire · 👊 Bravo · 😠 Colère · 😢 Triste.
  Une seule réaction par personne et par publication, modifiable ou retirable.
- **Commenter** chaque publication, compteur de commentaires.
- **Supprimer** ses propres publications (l'administration peut retirer tout contenu).
- Les photos sont servies par `/media/<fichier>` **derrière authentification** et vérifiées
  binairement (un faux `.png` est refusé).

---

## 6. Trois rôles seulement : Super Admin, Admin, Élèves — ✔

- Formulaire de compte : **3 choix exactement** — Élève (par défaut), Admin, Super Admin.
- Libellés harmonisés partout : badges, filtres, répartition des rôles, listes.
- Un **Admin** ne peut pas créer ni modifier un **Super Admin** (contrôle serveur).

---

## 7. Inscription d'un élève avec son dossier de classe — ✔

**Utilisateurs → Inscrire un élève** (`/admin/utilisateurs/nouveau`)

| Champ | Détail |
|---|---|
| **Nom** / **Prénom** | composent automatiquement le nom complet « Nom Prénom » |
| **Pseudo** | surnom affiché (classe, fil d'actualité, bulletin) |
| **Nom d'utilisateur sur le site** | 3 à 32 caractères, généré si laissé vide |
| **Numéro en classe** | nombre de 1 à 999 |
| **Niveau d'étude** | liste proposée (6ème → Master 2) + saisie libre |
| **Garçon / Fille** | obligatoire pour être comptabilisé dans les effectifs |
| **Groupe 1, 2 ou 3** | **modifiable** depuis le formulaire et depuis la fiche élève |

Exploitation : filtres par niveau et par groupe, tri par numéro, modification rapide du groupe,
export CSV complet, affichage dans le bulletin, et carte « Ma scolarité » côté élève (lecture seule).

---

## 8. Nouveau dans cette mise à jour — Liste de classe imprimable — ✔

**Administration → Scolarité → Liste de classe** (`/admin/classe`)

- Effectifs (total, garçons, filles, élèves notés).
- Élèves **répartis par groupe**, triés par **numéro en classe**.
- Colonnes : n°, nom, pseudo, niveau, sexe, **note /20**, mention.
- Bouton **Imprimer / PDF** avec feuille de style dédiée (menu et boutons masqués à l'impression).
- Réservée au **super administrateur** (403 pour les autres).

Deux améliorations liées :
- **Export des notes** (`/admin/notes/export.csv`) : colonnes numéro, nom, prénom, pseudo, niveau, groupe, sexe.
- Filtre de rôle affiché « **Élèves** » dans la liste des utilisateurs.

---

## Vérifications automatiques

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **42 tests réussis** |
| `tools/verify.py` (local) | **131 contrôles conformes** |
| `tools/verify.py` sur Render | **137 contrôles conformes, 0 échec** |
| PythonAnywhere | pages identiques, `/sante` ok, base migrée automatiquement |

Les dossiers de démonstration (`instance/`) ne sont **jamais** déployés : la production ne contient
que le compte `Myazirzk` et les comptes réellement créés par l'administration.
