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

## 12. Vague 7 — Connexion sur l'accueil, page « Découvrir », accueil simplifié — ✔

### 12.1 La connexion se trouve désormais sur la page d'accueil

On n'a plus besoin de quitter l'accueil : le formulaire est dans la **zone supérieure**,
immédiatement visible.

| Élément | Mise en œuvre |
|---|---|
| **Logo** | Logo animé (anneau, orbite, pastille) à côté du titre, 46 px, rendu identique en clair et en sombre. |
| **Titre accueillant** | « **Bienvenue sur TIC MASTER_#by_Myazirzk** » — le lien #by_Myazirzk reste cliquable vers l'onglet À propos. |
| **Sous-titre** | « Connectez-vous pour poursuivre votre apprentissage. » |
| **Identifiant** | Champ avec icône, autocomplétion `username`, majuscules désactivées, « suivant » sur le clavier mobile. |
| **Mot de passe** | Bouton **œil** pour afficher / masquer, `autocomplete="current-password"`, touche « go » qui valide. |
| **Se souvenir de moi** | Compatible avec la politique de sécurité : le cookie reste `HttpOnly` + `SameSite=Lax` (+ `Secure` en production), le jeton est aléatoire et **haché en base**, la session est **révocable**. Coché → 30 jours ; décoché → cookie de session (fermé avec le navigateur). |
| **Bouton principal** | « Se connecter », dégradé animé (filet lumineux), flèche qui glisse au survol. |
| **Indicateur de chargement** | Au clic : bouton désactivé, spinner, libellé « Connexion en cours… », `aria-busy="true"` ; réactivation automatique au retour (Android / bfcache). |
| **Erreurs claires** | « Identifiant ou mot de passe incorrect. » dans un encadré rouge, sans jamais révéler si le compte existe ; l'identifiant saisi est conservé, le mot de passe est effacé. |
| **Accessibilité / mobile** | Libellés associés (`for`/`id`), messages en `aria-live`, case personnalisée encore focusable au clavier, cibles ≥ 44 px, champs à 16 px (aucun zoom Android), carte pleine largeur dès 390 px. |

**Un seul backend d'authentification.** Le formulaire de l'accueil et celui de
`/auth/connexion` appellent la même fonction serveur `attempt_login()` : limitation
par IP, verrouillage du compte après échecs, messages génériques, journal d'audit,
cookie `HttpOnly` et session serveur révocable. `attempt_login()` ne renvoie jamais
le mot de passe et ne le stocke jamais : la vérification se fait par Argon2id.

### 12.2 Onglet « Programme » supprimé

- Le lien « Programme » a disparu du menu public (accueil, découvrir, à propos,
  connexion) et l'ancre `#programme` n'existe plus.
- Le menu public devient : **Accueil · Découvrir · À propos** (+ thème et
  « Se connecter » / « Mon espace »).
- Le programme détaillé (modules, leçons, durées, exercices) reste **exclusivement**
  dans l'espace de l'apprenant, selon les autorisations existantes.

### 12.3 Accueil radicalement simplifié

L'ancienne page (douze cartes de modules, description de chaque leçon, six
argumentaires, étapes, etc.) est remplacée par **deux blocs** :

1. **Bienvenue + connexion** (zone supérieure).
2. **« Apprenez les TIC autrement. »** — « Des cours pratiques, des exercices
   interactifs et des évaluations pour développer vos compétences numériques. »,
   puis **trois** éléments avec icône :
   - **Cours interactifs** — Apprenez à votre rythme.
   - **Exercices pratiques** — Testez vos connaissances.
   - **Évaluations** — Mesurez vos progrès.
   Et **un seul bouton secondaire** : « **Découvrir la plateforme** ».

### 12.4 Page « Découvrir la plateforme » (`/decouvrir`)

Page dédiée aux cours, volontairement synthétique : les trois piliers, « Comment
obtenir un accès » en trois étapes, le cadre de sécurité et un bouton de connexion.
**Aucune liste de modules** n'y figure : le programme complet n'apparaît qu'après
connexion, dans l'espace de l'apprenant.

### 12.5 Garanties conservées

- Aucune inscription publique, aucun bouton « Créer un compte ».
- Aucun compte ni mot de passe codé en dur dans le frontend ; aucun secret exposé au navigateur.
- Les comptes sont créés uniquement par l'administrateur autorisé.
- Sessions, mots de passe et autorisations restent gérés côté serveur.
- L'accueil est exempté du mode « mise à jour du site » : on peut toujours se connecter.

---

## 13. Vague 8 — Site joignable 24 h/24 (plus de « service waking up ») — ✔

### 13.1 Le problème

L'offre **gratuite** de Render endort un service web après **15 minutes sans
requête**. La visite suivante tombe alors sur la page *« service waking up »*
pendant une cinquantaine de secondes — ce qui donne l'impression que le site
est arrêté.

### 13.2 La solution : le site s'appelle lui-même

Dès que l'application tourne sur Render, un **fil discret** appelle
`https://ticmaster.onrender.com/sante` **toutes les 10 minutes** (premier appel
30 secondes après le démarrage). Chaque requête entrante remet à zéro le
compteur d'inactivité : le service ne s'endort plus et répond immédiatement,
**à n'importe quelle heure**.

**Mesure réelle (29/10)** : aucune visite extérieure pendant **26 minutes**,
puis une requête → **HTTP 200 en 0,24 s** (un réveil à froid aurait pris
30 à 50 s). Les journaux Render montrent les auto-appels toutes les 10 minutes
(`GET /sante … "TIC-MASTER-veille/1.0"` à 05:20:49, 05:30:49, 05:40:49,
05:50:50).

| Point | Détail |
|---|---|
| Mise en service | Automatique sur Render, grâce à la variable `RENDER_EXTERNAL_URL` fournie par l'hébergeur : **aucune configuration** à faire. |
| Coût | Offre gratuite conservée : 750 heures d'instance par mois, la veille en consomme ~730 (un seul service). |
| Charge | Un `GET /sante` (un simple `SELECT 1`) toutes les 10 minutes : négligeable. |
| Traçabilité | Les 20 derniers passages sont conservés dans `instance/veille.json` et affichés dans *Administration → Paramètres → Disponibilité 24 h/24*. |
| Panne | Si un appel échoue, le fil continue (aucune exception ne l'arrête) et l'erreur exacte est enregistrée. |
| Hors Render | Sur un poste de développement ou sur PythonAnywhere, la veille ne démarre pas. |

### 13.3 Pistes étudiées et écartées

- **PythonAnywhere comme réveil** : testé puis abandonné. Son proxy sortant
  refuse les sites non listés (`Tunnel connection failed: 403 Forbidden`) —
  l'appel n'arrive jamais à Render.
- **Robot GitHub Actions** : la tâche planifiée est prête (`veille.yml`),
  conservée hors du dépôt. Deux obstacles : le jeton OAuth des déploiements
  n'a pas le droit d'écrire dans `.github/workflows` (scope `workflow`
  manquant), et ce même jeton a expiré le 29/10 (voir §13.5).

### 13.4 Ce qui reste vrai

- Render redémarre le service à chaque déploiement : l'indisponibilité dure
  alors ~1 minute, le temps du build.
- Le réveil à froid ne peut plus se produire en usage normal ; il ne
  réapparaîtrait que si le fil de veille était interrompu (par exemple si
  l'instance épuisait les 750 heures du mois).

### 13.5 Jeton GitHub

Le jeton OAuth utilisé jusqu'ici a **expiré** le 29/10 (réponse `401`). Le compte
a été **reconnecté le même jour** par le « Device Flow » (code `7F1E-85ED`,
autorisé par `@rzkmyazi`), avec désormais les portées `repo` **et `workflow`** :
les fichiers `.github/workflows` peuvent être publiés. Le jeton n'est jamais
écrit sur le disque : il ne vit que le temps de la commande `git push`.
Les six commits en attente sont partis, Render s'est redéployé et les
**196 contrôles** y sont conformes.

---

## 14. Vague 9 — Fiche élève : suspendre, réinitialiser, supprimer — ✔

### 14.1 Ce qui se passait

Les trois boutons de la fiche (Réinitialiser le mot de passe, Suspendre,
Supprimer le compte) demandaient une confirmation par la **boîte de dialogue
native du navigateur** (`window.confirm`). Sur Android, Chrome peut **désactiver
définitivement** ces fenêtres (case « Empêcher cette page de créer d'autres
boîtes de dialogue ») : la confirmation ne s'affichait plus, le formulaire
n'était jamais envoyé… alors que le serveur, lui, fonctionnait. D'où l'impression
que rien ne marchait.

### 14.2 La correction

Une **boîte de dialogue intégrée** remplace toutes les confirmations natives :

| Point | Détail |
|---|---|
| Apparence | Fond assombri, panneau centré sur ordinateur, **feuille glissante** sur téléphone. |
| Contenu | Icône, titre parlant (« Suspendre le compte », « Réinitialiser le mot de passe », « Suppression définitive »), phrase qui nomme l'élève et l'effet de l'action. |
| Boutons | « Annuler » et un bouton d'action dont le libellé est explicite ; la suppression s'affiche en **rouge**. |
| Clavier / accessibilité | Touche **Échap** pour annuler, focus piégé dans la boîte, `role="dialog"`, `aria-modal`, retour du focus sur le bouton d'origine. |
| Impossibilité de blocage | Le navigateur ne peut pas la désactiver : elle fait partie de la page. |
| Secours | Si un navigateur très ancien n'a pas `requestSubmit`, on revient au `form.submit()` classique. |

### 14.3 Compléments

- **Réinitialisation** : après validation, la fiche **défile automatiquement
  jusqu'au nouveau mot de passe temporaire** et un message prévient qu'il ne
  sera plus affiché. Le mot de passe reste haché (Argon2id) et toutes les
  sessions de l'élève sont révoquées.
- **Suppression** : toujours protégée par la saisie du nom exact (« mauvais-nom »
  est refusé avec un message clair).
- La suppression d'une publication du fil utilise la même boîte (plus de
  `confirm` natif nulle part dans l'application).

### 14.4 Preuves

| Contrôle | Résultat |
|---|---|
| Navigateur Android simulé, `window.confirm` volontairement cassé | 0 dialogue natif, boîte affichée, action exécutée |
| Suspendre → statut « suspendu » et bouton devient « Réactiver » | ✔ |
| Réinitialiser → mot de passe temporaire affiché + bouton Copier | ✔ |
| Supprimer avec un nom erroné → refus explicite | ✔ |
| Supprimer avec le nom exact → compte supprimé, retour à la liste | ✔ |
| Aucune erreur JavaScript | ✔ |

---

## 15. Vague 10 — Notifications en temps réel — ✔

### 15.1 Le principe

Jusqu'ici, pour savoir qu'un message était arrivé, qu'une battle attendait une
validation ou qu'une annonce venait d'être publiée, il fallait **rouvrir les
pages** ou recharger. Désormais :

* une **cloche** est présente dans la barre du haut de toutes les pages privées,
  avec un **compteur rouge** du nombre de notifications non lues ;
* un clic ouvre un **panneau déroulant** avec les dernières notifications ;
* une **bannière discrète** apparaît en bas de l'écran dès qu'une nouveauté
  arrive — sans recharger la page, sans bloquer la lecture ;
* une page **« Notifications »** conserve l'historique complet, groupé par jour.

### 15.2 Ce qui déclenche une notification

| Événement | Destinataire | Texte de la notification |
|---|---|---|
| Message privé | Le destinataire | « Nouveau message de *nom* » + début du message |
| Battle déposée par un élève | Tous les administrateurs | « Battle à valider » + nom de l'élève et code |
| Quelqu'un rejoint une battle | Le créateur de la battle | « *nom* a rejoint votre battle » |
| Battle lancée | Tous les participants | « La battle « *nom* » démarre » |
| Annonce publiée | Tous les comptes actifs (jamais l'auteur) | « Nouvelle annonce : *titre* » |
| Examen corrigé | L'élève | « Votre examen est corrigé » + note /20 |
| Mot de passe réinitialisé par l'administration | L'élève | « Votre mot de passe a été réinitialisé » |
| Compte suspendu / réactivé | L'élève | « Votre compte a été suspendu » / « de nouveau actif » |

Toutes ces notifications sont **réelles** : elles sont créées par le serveur au
moment où l'action a lieu, enregistrées en base, et propres à chaque compte.
Aucune n'est simulée ni fabriquée côté navigateur.

### 15.3 Comment le navigateur les reçoit

| Point | Détail |
|---|---|
| Fréquence | Une requête légère (`/api/notifications`) toutes les **25 secondes**. |
| Onglet en arrière-plan | **Aucune requête** : le rafraîchissement reprend dès le retour sur la page (et au retour de focus). |
| Bandeau | Affiché 6 secondes, un maximum de 3 nouveautés à la fois, sinon simple mise à jour du compteur. |
| Premier chargement | Aucune bannière : seuls les événements **postérieurs** à l'ouverture de la page déclenchent une alerte. |
| Compteur à zéro | Cas particulier corrigé : quand on n'avait **aucune** notification, la toute première nouveauté déclenche bien sa bannière (le curseur `since=0` est transmis explicitement). |
| Rien de bloquant | Aucune fenêtre native, aucun clignotement : la bannière apparaît et disparaît en fondu. |
| Économie | La réponse ne contient que 8 notifications et un compteur ; rien n'est rechargé d'autre. |
| Panneau toujours juste | Ouvrir le panneau affiche immédiatement les dernières données reçues puis interroge le serveur : jamais de liste vide à tort. |
| Bannière lisible | Le nom de l'auteur n'est pas répété quand le titre le contient déjà (« Nouveau message de … »). |

### 15.4 Lecture et historique

- Ouvrir le panneau marque les notifications affichées comme lues (le compteur
  retombe) ; « Tout marquer comme lu » fait la même chose d'un coup.
- La page **/notifications** liste tout, **groupée par jour**, avec l'auteur,
  l'heure et une pastille rouge pour ce qui reste à lire.
- Chaque notification est un **lien direct** vers l'endroit concerné (le fil de
  discussion, la battle, l'annonce, le résultat d'examen) ; seuls les chemins
  internes sont acceptés, ce qui exclut toute redirection vers un site externe.

### 15.5 Données et discrétion

| Règle | Détail |
|---|---|
| Une ligne par destinataire | La suppression d'un compte efface ses notifications (cascade). |
| Pas d'auto-notification | On n'est jamais prévenu de sa propre action. |
| Ménage automatique | Les notifications lues de plus de **45 jours** sont effacées ; **200** au maximum par personne. |
| Permissions | Seul le propriétaire peut lire et marquer ses notifications : l'API filtre systématiquement par compte. |

### 15.6 Preuves

| Contrôle | Résultat |
|---|---|
| Cloche et compteur sur téléphone Android simulé (Pixel, 393 px) | ✔ |
| Panneau déroulant ouvert au clic | ✔ |
| Nouvelle notification insérée en base → compteur 0 → 1 et bannière | ✔ |
| Page d'historique : notifications groupées par jour | ✔ |
| Première notification alors que le compteur était à zéro → bannière affichée | ✔ |
| Erreurs JavaScript | aucune |
| Message privé du super admin → notification immédiate chez l'élève | ✔ |
| Annonce publiée → tous les comptes actifs notifiés, jamais l'auteur | ✔ |
| Battle déposée par un élève → administrateurs notifiés | ✔ |
| Le compteur retombe après lecture | ✔ |
| Cloche absente de la page publique | ✔ |

Captures : `apercus/android/prod-notifications-panneau.png`,
`prod-notifications-banniere.png`, `prod-notifications-historique.png`.

---

## 16. Vague 11 — Le professeur et la messagerie de classe — ✔

### 16.1 Le super administrateur est un professeur

Le super administrateur (et l'administrateur) **enseignent** : ils ne suivent pas
de programme et ne passent pas d'exercices. L'interface le reflète maintenant
partout.

| Avant | Maintenant |
|---|---|
| Menu « Cours & modules » et « Exercices » (parcours d'élève) | Menu **« Espace professeur »** : *Mes cours*, *Mes exercices*, *Ressources* |
| « Examens trimestriels » et « Mes résultats » pour les administrateurs | Masqués pour tout le personnel |
| « Mon historique » (parcours d'apprenant) | Réservé aux élèves |
| `/espace` affichait 0 % de progression pour un administrateur | Renvoi vers l'accueil professeur |
| `/cours`, `/exercices`, `/examens`, `/resultats` accessibles au professeur | Renvois vers la gestion correspondante |

Contrôles côté **serveur** (masquer un menu ne suffit pas) : les redirections
sont faites dans les vues, avec un message explicite (« Espace professeur : vos
cours se gèrent dans Modules & leçons »). L'accueil du professeur s'intitule
« Bonjour … » et rassemble les indicateurs de la classe.

### 16.2 Messagerie de classe

Un professeur peut désormais écrire **à toute une classe en une fois**.

| Fonction | Détail |
|---|---|
| Cibles | Toute la classe, un **niveau** (« Terminale », « 1ère »), un **groupe** (1 → 99), ou niveau + groupe |
| Envoi | Un seul message, une seule action ; chaque élève visé reçoit une **notification** |
| Écriture | Réservée au professeur : un élève reçoit une erreur 403 s'il tente d'écrire dans le salon de classe |
| Lecture | Chaque élève ne voit **que** les salons de sa classe ; un autre groupe n'y a aucun accès |
| Réponse | L'élève répond en privé au professeur (bouton « Répondre au professeur en privé ») |
| Repérage | Les salons de classe portent l'icône mégaphone et un compteur de messages non lus |

### 16.3 Accusés de lecture

| Fonction | Détail |
|---|---|
| Enregistrement | Un lecteur = une ligne (table `message_reads`), jamais de doublon |
| Dans les messages privés | « Envoyé » puis « Lu » dès que le destinataire ouvre la conversation |
| Dans un message de classe | « Lu par 3/28 » — le professeur sait combien d'élèves ont lu |
| Rafraîchissement | Toutes les 4 s pour les nouveaux messages, toutes les 12 s pour les accusés |
| Vie privée | Aucun accusé de lecture sur ses propres messages ; rien n'est affiché dans le salon général |

### 16.4 Sur Android

La liste des conversations (classe, privés, membres) devient une **bande
horizontale défilante** : la conversation occupe presque tout l'écran, la
conversation ouverte est automatiquement amenée sous les yeux de l'utilisateur,
et le composeur reste accessible au-dessus de la barre d'onglets.

### 16.5 Deux défauts corrigés au passage

| Problème constaté en production | Correction |
|---|---|
| La **photo de profil disparaissait** après un redéploiement (disque éphémère de Render) : l'image renvoyait une erreur 404 et s'affichait cassée | La photo est désormais **copiée dans la base** en plus du fichier ; si le fichier a disparu, elle est servie depuis la base. Si l'image n'existe plus du tout, les **initiales sont dessinées** (aucune image cassée). |
| Le menu « Trier » de la page Notes et le bouton « Actualiser » ne faisaient rien : leurs gestionnaires `onclick`/`onchange` étaient **bloqués par la politique de sécurité (CSP)** | Plus aucun gestionnaire en ligne dans les pages : les comportements passent par `data-auto-submit`, `data-reload` et `data-back`, branchés dans `app.js`. |

### 16.6 Preuves

| Contrôle | Résultat |
|---|---|
| Menu professeur : « Mes cours », « Mes exercices », aucun parcours d'élève | ✔ |
| `/cours`, `/exercices`, `/examens`, `/resultats`, `/espace` renvoyés côté professeur | ✔ |
| Message du professeur à un groupe → seul ce groupe est notifié | ✔ |
| Élève visé : message reçu, notification reçue | ✔ |
| Élève d'un autre groupe : 403 et salon invisible | ✔ |
| Élève tentant d'écrire à la classe : 403 | ✔ |
| Accusés de lecture remontés (« Lu », « Lu par n/N ») | ✔ |
| Aucune erreur JavaScript sur Android simulé | ✔ |

Captures : `apercus/android/prof-accueil.png`, `prof-message-classe.png`,
`eleve-message-classe.png`, `prof-mes-cours.png`.

---

## 17. Vague 12 — Battle réparée, messages transférés, notifications affinées — ✔

### 17.1 Pourquoi la battle ne marchait pas

La battle était **inutilisable de bout en bout**, solo comme en groupe : appuyer sur
« Créer une battle » ne produisait rien du tout.

| Cause | Détail |
|---|---|
| **Jeton de sécurité introuvable** | Le script `battle.js` lisait le jeton CSRF dans une variable (`window.TIC_CSRF`) qui n'existe que sur les pages d'examen. Sur les autres pages la valeur était vide : le serveur refusait chaque appel (`400 Jeton CSRF invalide`) — création, code d'accès, lancement et réponses. |
| **Erreurs muettes** | Les messages d'erreur étaient envoyés à une fonction (`window.ticToast`) qui n'existait pas : aucune alerte ne s'affichait, l'écran restait figé. |
| **Bouton « Lancer » bloqué** | Le bouton était rendu inactif pour une demande en attente et **n'était jamais réactivé** une fois la battle acceptée par le professeur. |

Correctifs : le jeton est désormais lu dans la balise `<meta name="csrf-token">` (présente sur
**toutes** les pages), l'ancien nom `ticToast` est branché sur les notifications réelles de
l'application, et le bouton de lancement comme la bannière « en attente de validation » se
mettent à jour en direct quand le professeur accepte.

### 17.2 La battle est aussi plus vivante

* **Avancement immédiat** : dès que tous les joueurs ont répondu, la question suivante part.
  On n'attend plus 20 secondes pour rien (les 20 s restent la limite maximale).
* **Attente expliquée** : « Réponse enregistrée · en attente de 1 joueur ».
* **Notification d'acceptation** : l'élève reçoit une alerte « Votre battle est acceptée »
  (ou « a été refusée ») avec le lien direct vers la salle.
* Le renommage d'un groupe met à jour le titre affiché sans recharger la page.
* Sur la page « changement de mot de passe obligatoire », la cloche est mise en veille :
  l'API étant fermée à ce moment-là, elle n'affiche plus d'erreur inutile dans la console.

### 17.3 Transférer un message, et savoir qu'il est arrivé

| Nouveauté | Détail |
|---|---|
| **Bouton Transférer** | Sous chaque message, une flèche ouvre une fenêtre : on choisit la destination (salon général, message de classe pour le professeur, conversation privée) et le message part tel quel. |
| **Auteur d'origine affiché** | Le message transféré porte la mention « Message transféré de … » avec la date de l'original. Le texte n'est jamais modifiable : aucune usurpation possible. |
| **Trois états** | « **Envoyé** » (le serveur a le message), « **Reçu** » (le navigateur du destinataire l'a atteint), « **Lu** » (la conversation a été ouverte). La remise est enregistrée par la cloche des notifications et par l'ouverture du fil. |
| **Contrôles serveur** | Impossible de transférer un message d'une conversation dont on n'est pas partie (403), de renvoyer un message vers son propre salon (400) ou de réécrire l'original. |

### 17.4 Notifications plus utiles

* **Filtres par type** en haut de l'historique : Tout, Message, Battle, Annonce, Note, Compte,
  Système — avec le nombre de non-lues en pastille rose.
* **Acceptation / refus d'une battle** notifiés à l'élève concerné.
* **Remise des messages privés** déclenchée au passage de la cloche : le professeur voit
  « Reçu » avant même que l'élève ouvre la conversation.
* **Vider les lues** : un bouton retire de la liste les notifications déjà lues ; les non lues
  sont toujours conservées.

### 17.5 Preuves

| Contrôle | Résultat |
|---|---|
| Battle solo : création → validation → lancement → 3 questions → fin de partie | ✔ |
| Battle en groupe : 2 joueurs, code, renommage, scores 2 / 2, corrections | ✔ |
| « Reçu » puis « Lu » sur un message privé | ✔ |
| Message transféré visible avec son auteur d'origine | ✔ |
| Filtres de notifications (`?type=message`) | ✔ |
| Aucune erreur JavaScript sur Android simulé | ✔ |

Captures : `apercus/android/battle-solo-fini.png`, `battle-groupe-fini.png`,
`v12-messages-accuses.png`, `v12-transferer.png`, `v12-message-transfere.png`,
`v12-notifications-filtres.png`.

---

## 18. Vague 13 — Créer un compte, puis se connecter sans se tromper — ✔

### 18.1 Pourquoi « identifiant ou mot de passe incorrect » juste après une création

Trois défauts se cumulaient, tous invisibles pour l'administrateur :

| Défaut | Ce que vivait l'utilisateur |
|---|---|
| **Identifiant illisible** : généré en collant le nom et en coupant à 14 caractères (« Kanto Rasoanaivo » → `kantorasoanaiv`) | L'élève tapait son nom ou une orthographe logique : `kanto.rasoanaivo` → refus. |
| **Espaces du clavier mobile** : le mot de passe temporaire saisi par l'administrateur gardait ses espaces de bord | Le mot de passe **affiché** ne correspondait pas à celui réellement enregistré. |
| **Seul l'identifiant exact fonctionnait** | Le nom complet, le pseudo, l'adresse e-mail ou une majuscule de trop donnaient le même message générique. |

### 18.2 Les corrections

* **Identifiant lisible** : `Kanto Rasoanaivo` → **`kanto.rasoanaivo`** (nom + initiale conservés, accents
  retirés, suffixe `2`, `3`… en cas de doublon). Il est affiché dans la carte « Compte créé ».
* **Espaces de bord retirés** à l'enregistrement du mot de passe imposé, avec un message explicite :
  le mot de passe affiché est exactement celui qui fonctionne.
* **Connexion tolérante** — le champ accepte indifféremment :
  l'**identifiant** (insensible à la casse et aux espaces), l'**adresse e-mail**, le **pseudo**,
  le **nom complet**, ou la forme aplatie sans accents ni ponctuation. La forme approchée n'ouvre un
  compte que si **une seule** correspondance existe : impossible d'entrer dans le compte d'un autre.
* Une **espace finale** ajoutée par le clavier au mot de passe est ignorée (la saisie exacte est
  toujours essayée d'abord, donc un mot de passe volontairement entouré d'espaces reste valable).
* **Erreur de création éclairante** : le message apparaît en haut, la page défile jusqu'à lui et il est
  écrit noir sur blanc : « **Le compte n'a pas été créé : mot de passe trop faible (…)** ».
* **Contrôle en direct** de la politique de mot de passe : cinq pastilles se colorent à mesure de la saisie.
* **Deux boutons de copie** (identifiant / mot de passe) au lieu d'un seul, un lien direct vers la page
  de connexion, et le même confort sur la fiche élève après une réinitialisation.
* La page de connexion explique la **première connexion** : majuscules, aucune espace, et les
  identifiants acceptés.

### 18.3 Preuves

| Contrôle | Résultat |
|---|---|
| Création « Kanto Rasoanaivo » → identifiant `kanto.rasoanaivo` | ✔ |
| Connexion avec l'identifiant affiché (200 créés sur Render et PythonAnywhere) | ✔ |
| Mot de passe saisi `Espace2026!  ` → enregistré `Espace2026!`, connexion OK | ✔ |
| Connexion par nom complet, majuscules, espaces, pseudo, e-mail, forme aplatie | ✔ 8 variantes |
| Mot de passe faux toujours refusé | ✔ |
| Mot de passe trop faible : aucun compte créé + message clair | ✔ |

Captures : `apercus/android/v13-connexion.png`, `v13-politique.png`, `v13-erreur.png`,
`v13-compte-cree.png`.

---

## 19. Mise à jour du 30/10/2026 — Connexion simultanée multi-utilisateurs (vague 14)

### 19.1 Ce qui a été vérifié avant toute modification

Le socle serveur était déjà multi-utilisateurs : une table `auth_sessions`, un jeton aléatoire par
connexion (stocké **haché en SHA-256**), un cookie `HttpOnly`, aucun écrasement de session.

| Scénario mesuré | Résultat |
|---|---|
| Deux comptes différents en même temps | ✔ |
| Même compte sur deux navigateurs (le premier reste connecté) | ✔ |
| 30 connexions simultanées depuis la même adresse IP | 30 / 30 ✔ |
| Trois erreurs de mot de passe d'affilée | ✔ aucune gêne |
| **13 erreurs d'affilée puis le bon mot de passe** | ✘ **toute l'adresse IP bloquée** |

Le défaut réel se situait donc dans **la limite anti-force brute par adresse IP** : elle comptait
*chaque tentative*, réussie ou non. Derrière la box d'une salle de classe, un seul élève qui se trompe
plusieurs fois privait **toute la classe** de connexion pendant dix minutes.

### 19.2 Corrections apportées

* **La limite par IP ne compte plus que les échecs** (`limiter.blocked` en amont, `limiter.hit`
  uniquement sur mot de passe faux ou compte inconnu) et le seuil passe de 12 à **40 échecs / 10 min** :
  une classe entière peut travailler normalement, y compris après des fautes de frappe.
* **Le verrouillage par compte** (8 erreurs → 15 minutes) est conservé : il protège le compte visé,
  **jamais** ceux des autres. Un bouton **« Déverrouiller le compte »** apparaît sur la fiche de
  l'élève concerné pour que le professeur le libère sur-le-champ, sans changer son mot de passe.
* **Règle d'appareils par compte, réglable par l'administrateur** (`/admin/parametres`) :
  *illimité* (défaut), 1, 2, 3, 5 ou 10 appareils simultanés. Au-delà, seules les sessions les plus
  anciennes **du compte concerné** sont fermées — les autres personnes ne sont jamais touchées.
* **Page « Utilisateurs connectés »** (`/admin/sessions`), ouverte aux administrateurs comme au
  super administrateur : personne, **appareil** (« Android · Chrome », « iPhone · Safari », « Windows ·
  Chrome », « Robot / script »), heure de connexion, dernière activité, expiration, adresse IP, état
  (En ligne / Ouverte / Fermée), recherche par nom, filtre « sessions ouvertes seulement » et
  **fermeture individuelle** d'une session. La session courante et celles des super administrateurs
  sont protégées.
* **Carte « Qui est connecté maintenant »** sur le tableau de bord : nom, appareil, nombre d'appareils,
  dernière activité, lien vers la page complète. **Rafraîchissement automatique toutes les 20 secondes**
  via `GET /admin/api/presence` (aucun rechargement de page, aucune gêne pour les connectés).
* **Déconnexion globale d'un compte** (`POST /admin/utilisateurs/<id>/deconnecter`) : ferme toutes ses
  sessions sans suspendre le compte.
* **Aucun secret dans le navigateur** : le jeton de session reste dans un cookie `HttpOnly` ; l'API de
  présence ne renvoie que nom, appareil, adresse IP et horodatages.

### 19.3 Preuves (serveur local, 30/10/2026)

| Contrôle | Résultat |
|---|---|
| Deux comptes différents connectés simultanément | ✔ |
| Le premier reste connecté après la connexion du second | ✔ |
| Même compte sur deux appareils, les deux vivants | ✔ |
| 30 connexions simultanées depuis la même IP | **30 / 30** ✔ |
| 13 erreurs sur un compte → les autres comptes se connectent toujours | ✔ |
| 13 erreurs sur un compte → ce compte est verrouillé, puis déverrouillé par l'administrateur | ✔ |
| Règle « 1 appareil » : seul l'ancien appareil du compte visé est fermé | ✔ |
| Retour à « illimité » : la règle disparaît sans redémarrage | ✔ |
| Révocation d'une session : un appareil tombe, l'autre continue | ✔ |
| Page de présence interdite à un élève (403) | ✔ |
| Tableau de bord : compteur vivant (4 en ligne → 3 après révocation) | ✔ |

Captures : `apercus/android/v14-sessions.png`, `v14-presence.png`, `v14-reglage-appareils.png`.

---

---

## 20. Mise à jour du 30/10/2026 — Audit et optimisation V2.1

Rapport complet : [`docs/AUDIT-V2.1.md`](AUDIT-V2.1.md).

### 20.1 Ce que l'audit de production a établi

Sur 97 sessions enregistrées le 30/10/2026 : **64 scripts de vérification** du
projet, **6 captures automatisées**, **3 scripts d'audit**, **17 sessions
réelles**. Les « Robot / script » n'étaient donc pas des attaquants mais les
outils du projet, qui ne se déconnectaient jamais. Aucune session n'est créée
par un rechargement de page (10 rechargements → 0 session).

Trois défauts réels : états confondus (« Fermée » = expirée **ou** révoquée),
aucune purge, heuristique « robot » trop large.

### 20.2 Corrections

* **5 états** : En ligne (vert), Inactive (gris), Expirée (ambre), Révoquée
  (rouge), session courante.
* **Détection d'appareil** refondue : Android 13 · Chrome, iPhone · Safari,
  Windows 10 · Edge, Linux (Ubuntu) · Firefox, macOS · Safari, modèle Android ;
  les vrais robots portent « Script · … » ; un navigateur inconnu n'est plus un
  robot.
* **Nettoyage** : rétention réglable (30 j par défaut), purge horaire
  opportuniste, action manuelle avec simulation ; les sessions ouvertes ne sont
  jamais touchées.
* **Durée de connexion** réglable (1 h → 30 j), **détection de changement
  d'appareil** journalisée (vol de cookie).
* **Filtres** (personne, appareil, état, activité, date, tri, pagination) et
  **actions** (fermer une session, toutes celles d'une personne, sessions
  automatisées, nettoyage).
* **Historique des connexions** (`/admin/connexions`).
* **Performance** : Argon2id 19 Mio (au lieu de 64), présence écrite une fois
  par minute, index sur `auth_sessions` et `audit_logs`.

### 20.3 Résultats

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **114 réussis** |
| `tools/verify.py` (local) | **275 conformes, 0 échec** |
| `tools/test_sessions.py` (A → G) | **31/31 conformes** |
| `tools/load_test.py` — 200 sessions | **200/200**, médiane 3,5 s |
| `tools/load_test.py` — 400 sessions | **400/400**, 19,8 sessions/s |

Captures : `apercus/android/v15-sessions.png`, `v15-en-ligne.png`,
`v15-historique.png`, `v15-tableau-de-bord.png`, `v15-reglages-sessions.png`,
`apercus/v15-sessions-bureau.png`.

---

---

## Vérifications automatiques

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **114 tests réussis** |
| `tools/verify.py` (local) | **275 contrôles conformes, 0 échec** |
| `tools/test_sessions.py` (scénarios A → G) | **31/31 conformes** |
| `tools/load_test.py` (200 puis 400 sessions) | **200/200** et **400/400** |
| `tools/verify.py` sur Render | **277 contrôles conformes, 0 échec** |
| `tools/verify.py` sur PythonAnywhere | **277 contrôles conformes, 0 échec** |
| `tools/test_sessions.py` sur Render et PythonAnywhere | **31/31 conformes** |

Les dossiers de démonstration (`instance/`) ne sont **jamais** déployés : la production ne contient
que le compte `Myazirzk` et les comptes réellement créés par l'administration.
