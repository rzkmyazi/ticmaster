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

## 9. Vague 4 — Connexion épurée, photo de profil, onglet Bulletins, groupe — ✔

| Demande | Réponse | Où vérifier |
|---|---|---|
| « Effacer le détail du programme dans la page de login » | La page de connexion est **une carte unique centrée** : plus de panneau latéral, plus de liste des fonctionnalités, plus de lien « Programme » sur cet écran. | `/auth/connexion` |
| « Modifier sa photo de profil en uploadant dans la galerie » | Bouton **Changer la photo** dans *Mon profil → Mes informations* : accepte PNG, JPG, GIF, WEBP (30 Mo max), aperçu immédiat, bouton **Retirer**. La photo remplace les initiales partout (menu, fil, messages, listes, bulletins). | `/mon-profil` |
| « Un onglet Bulletins qui affiche le bulletin de chaque élève » | Nouvel onglet **Bulletins** (`/admin/bulletins`) : une fiche par élève avec **note /20**, mention, rang, résultats par module et par trimestre, progression, bouton **Bulletin complet** et **Imprimer tous les bulletins**. | Menu *Scolarité → Bulletins* |
| « Dans le dossier scolaire, le groupe est modifiable ; le Super Admin l'insère et choisit le groupe » | Le groupe (1, 2, 3) est **modifiable à tout moment** depuis la fiche élève ; **seul le super administrateur** peut le choisir — un administrateur voit le groupe **en lecture seule**, et le serveur refuse tout changement (le groupe reste inchangé). | `/admin/utilisateurs/<élève>` |

Détails techniques :

- **Photo de profil** : colonne `users.avatar_filename` (ajoutée automatiquement au démarrage, aucune migration manuelle). Routes : `POST /mon-profil/photo` (envoi / `action=remove`) et `GET /avatar/<fichier>` — cette dernière **exige une connexion** et renvoie **404** pour un fichier inconnu. Le fichier est contrôlé par sa **signature binaire** : un `.php` renommé en `.png` est refusé.
- **Onglet Bulletins** : réservé au super administrateur (403 pour un administrateur ou un élève), calculé sur les **vraies copies** (`Attempt`), pas de note simulée. Le lien n'apparaît pas dans le menu des autres rôles.
- **Groupe** : contrôle **côté serveur** (`POST /admin/utilisateurs/<id>/classe`) — la valeur est ignorée si l'auteur n'est pas super administrateur, même avec une requête forgée.
- **Bonus de robustesse** : SQLite applique désormais `PRAGMA foreign_keys=ON`, donc la suppression d'un compte efface réellement ses données liées (copies, battle, messages, publications) comme sur PostgreSQL ; et une battle terminée ne bloque plus la création d'une nouvelle.

---

## 10. Vague 5 — Questions des battles & groupes libres — ✔

### 10.1 L'administrateur et le super administrateur créent les questions des battles

| Étape | Où | Détail |
|---|---|---|
| 1 | **Administration → Battles à valider** (`/admin/battles`) | chaque demande (solo **ou groupe**) affiche une colonne **Questions** avec le nombre |
| 2 | Clic sur le badge **Questions** | écran **Questions de la battle** (`/admin/battles/<id>/questions`) |
| 3 | Colonne de gauche | cocher les questions existantes dans la banque (recherche, « tout cocher »), puis **Enregistrer la sélection** |
| 4 | Colonne de droite | **Créer une question** : énoncé, 2 à 4 propositions, bonne réponse, points, explication — elle est **ajoutée immédiatement** à la battle |
| 5 | | Accepter la demande, puis l'élève démarre la battle : **ce sont ces questions qui sont posées** |

- Accessible à **l'administrateur** et au **super administrateur** (`admin_required`) ; un élève reçoit **403**.
- Modifiable **uniquement avant le démarrage** (sinon retour à la liste avec un message).
- Les questions créées depuis cet écran sont rangées dans l'exercice brouillon « **Banque de questions Battle** » (invisible pour les élèves), ou dans l'exercice de votre choix.
- Les questions déjà créées dans *Administration → Exercices* sont utilisables aussi : la banque les propose toutes (au moins 2 propositions requises).

### 10.2 Le groupe du dossier scolaire accepte n'importe quel numéro

| Avant | Maintenant |
|---|---|
| seulement 1, 2 ou 3 | **1, 2, 3… jusqu'à 99** — le super administrateur saisit le numéro qu'il veut |

- Champ **numérique avec suggestions** (1, 2, 3 + tous les groupes déjà utilisés) dans le formulaire d'inscription et dans la fiche élève.
- La **liste de classe**, l'**export CSV**, les **filtres** et les **bulletins** affichent automatiquement « Groupe 4 », « Groupe 12 »…
- Contrôle serveur : `0`, `100` ou une valeur non numérique sont **refusés** (message explicite) ; un **administrateur** ne peut toujours pas changer le groupe (lecture seule).

---

## 11. Vague 6 — Vue Android améliorée & connexion sans changement d'onglet — ✔

### 11.1 Le site est pensé pour le téléphone

| Amélioration | Détail |
|---|---|
| **Barre d'onglets fixe en bas** | Nouvelle navigation rapide, toujours visible, avec l'onglet de la page courante surligné : **Accueil · Cours · Exercices · Battle · Messages · Profil** (élève) et **Accueil · Élèves · Notes · Messages · Profil** (super administrateur ; **Accueil · Élèves · Cours** pour un administrateur). |
| **Zones tactiles** | Boutons, liens de menu, onglets et icônes font au moins **44 px** de haut ; le menu latéral devient un tiroir lisible (48 px par lien). |
| **Champs sans zoom** | Tous les champs passent à **16 px** sur mobile : Android ne zoome plus automatiquement quand on tape, la page ne « saute » plus. |
| **Encoche et barre gestuelle** | Marges de sécurité (`env(safe-area-inset-…)`) en haut et en bas : rien n'est masqué par la barre de navigation du téléphone. |
| **Lisibilité** | Barre du haut compacte (le sous-titre n'occupe plus 3 lignes), cartes de statistiques en **2 colonnes** dès 360 px, icônes réduites, actions de page sur deux colonnes. |
| **Tableaux** | Défilement horizontal fluide avec repère visuel ; aucun débordement horizontal sur les pages testées (0 px). |
| **Confort** | `100dvh` (plus de barre d'adresse qui coupe le contenu), pas d'effet de survol collant au doigt, boutons réactivés au retour depuis l'historique Android. |
| **Installation** | Métadonnées « mobile web app » : ajout à l'écran d'accueil depuis Chrome, ouverture plein écran via le manifeste. |
| **Mise à jour visible** | Service worker en version 2 (stale-while-revalidate) : un nouveau design arrive **dès la deuxième visite**, sans vider le cache à la main. |

### 11.2 Page de connexion : plus de changement d'onglet

- Le module d'authentification forçait le clavier du téléphone à s'ouvrir : la page se décalait et le bouton **Se connecter** passait sous le clavier → impression de « changement d'onglet ». Le focus automatique est désormais réservé aux écrans avec souris ; sur tactile, la page reste **parfaitement stable**.
- Le bouton **« Se connecter »** du menu public est masqué lorsque l'on est **déjà** sur la connexion (plus de doublon en haut et au milieu).
- Le clavier affiche **« suivant »** puis **« go »** : la touche Entrée enchaîne identifiant → mot de passe → connexion.
- Titre et logo de la page restaurés : le logo animé (anneau + pastille) est de nouveau visible à côté de « Connexion », sur une seule ligne, sans texte coupé.
- Aucune barre d'onglets sur les écrans publics : la connexion reste une page isolée.

---

## Vérifications automatiques

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **50 tests réussis** |
| `tools/verify.py` (local) | **169 contrôles conformes, 0 échec** |
| `tools/verify.py` sur Render | *(mesuré après déploiement)* |
| `tools/verify.py` sur PythonAnywhere | *(idem)* |

Les dossiers de démonstration (`instance/`) ne sont **jamais** déployés : la production ne contient
que le compte `Myazirzk` et les comptes réellement créés par l'administration.
