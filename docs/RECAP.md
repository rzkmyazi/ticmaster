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

## Vérifications automatiques

| Contrôle | Résultat |
|---|---|
| `pytest -q` | **70 tests réussis** |
| `tools/verify.py` (local) | **206 contrôles conformes, 0 échec** |
| `tools/verify.py` sur Render | **208 contrôles conformes, 0 échec** |
| `tools/verify.py` sur PythonAnywhere | **208 contrôles conformes, 0 échec** |

Les dossiers de démonstration (`instance/`) ne sont **jamais** déployés : la production ne contient
que le compte `Myazirzk` et les comptes réellement créés par l'administration.
