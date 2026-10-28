# -*- coding: utf-8 -*-
"""Contenu pédagogique TIC MASTER — 11 modules progressifs + évaluations.

Chaque module contient des leçons (texte structuré façon Markdown),
un exercice corrigé et, pour les modules clés, des questions d'examen.
"""

CATEGORIES = [
    ("Fondamentaux", "Decouverte de l'informatique et des TIC", "chip"),
    ("Bureautique", "Traitement de texte, tableurs, presentations", "grid"),
    ("Internet & Web", "Navigation, communication, services en ligne", "globe"),
    ("Sécurité & Réseaux", "Protection des donnees et infrastructures", "shield"),
    ("Développement", "Programmation et creation de sites web", "code"),
    ("Intelligence Artificielle", "IA, donnees et usages responsables", "sparkles"),
]

MODULES = [
    {
        "title": "Introduction aux TIC",
        "category": "Fondamentaux",
        "level": "débutant",
        "estimated_minutes": 90,
        "summary": "Comprendre ce que sont les Technologies de l'Information et de la Communication et leur impact sur la société.",
        "description": "Ce module d'ouverture présente les concepts de base : information, numérique, matériel, logiciel, réseaux et usages citoyens des TIC.",
        "lessons": [
            ("Qu'est-ce que les TIC ?", """## Définition

Les **Technologies de l'Information et de la Communication** (TIC) désignent l'ensemble des outils et techniques permettant de **produire, stocker, traiter, transmettre et diffuser** de l'information sous forme numérique.

On distingue trois grandes familles :

- **Le matériel** : ordinateurs, téléphones, tablettes, serveurs, routeurs, capteurs.
- **Les logiciels** : systèmes d'exploitation, applications bureautiques, navigateurs, services en ligne.
- **Les réseaux** : Internet, réseaux mobiles, réseaux locaux d'entreprise.

## Pourquoi c'est important

Une photographie prise avec un téléphone est une **donnée numérique**. Cette même photo peut être :

1. stockée dans la mémoire du téléphone (stockage) ;
2. retouchée avec une application (traitement) ;
3. envoyée par messagerie (transmission) ;
4. publiée sur un réseau social (diffusion).

> Le numérique transforme l'information en une ressource que l'on peut copier, partager et analyser à très grande vitesse.

## Les usages concrets au quotidien

- **Éducation** : cours en ligne, exercices interactifs, bibliothèques numériques.
- **Santé** : dossiers médicaux informatisés, téléconsultation.
- **Administration** : démarches en ligne, paiement des taxes, état civil.
- **Économie** : mobile money, commerce en ligne, télétravail.

## Les limites à connaître

Les TIC ne sont pas neutres : elles demandent de l'**électricité**, une **connexion**, des **compétences** et une vraie **vigilance sur la vie privée**. Un bon usage suppose donc de comprendre à la fois les possibilités et les risques.
"""),
            ("Le vocabulaire essentiel du numérique", """## Les mots à maîtriser

- **Donnée** : une valeur brute (un nombre, une date, une photo).
- **Information** : une donnée interprétée dans un contexte.
- **Numérique** : information codée en 0 et 1 (binaire).
- **Bit** : plus petite unité d'information (0 ou 1). Un **octet** (byte) = 8 bits.
- **Application** : programme conçu pour accomplir une tâche.
- **Réseau** : ensemble d'équipements reliés entre eux pour échanger des données.

## Les unités de mesure

| Unité | Valeur approximative |
|---|---|
| 1 Ko (kilooctet) | 1 000 octets |
| 1 Mo (mégaoctet) | 1 000 000 octets |
| 1 Go (gigaoctet) | 1 000 000 000 octets |
| 1 To (téraoctet) | 1 000 000 000 000 octets |

Une page de texte ≈ 3 Ko. Une photo de téléphone ≈ 4 Mo. Un film ≈ 2 Go.

## Analogie utile

Pensez à une **bibliothèque** :

- le **disque dur** est le bâtiment (stockage) ;
- les **fichiers** sont les livres ;
- le **système d'exploitation** est le bibliothécaire qui sait où ranger et retrouver chaque livre ;
- le **réseau** est le service de livraison entre bibliothèques.

## À retenir

Comprendre ces mots, c'est pouvoir lire une fiche technique, choisir un forfait Internet ou expliquer un problème technique avec précision.
"""),
            ("Les métiers et les usages citoyens", """## Des métiers variés

Les TIC génèrent des emplois très différents :

- **Développeur web** : crée des sites et applications.
- **Administrateur réseau** : assure le bon fonctionnement des connexions.
- **Technicien support** : aide les utilisateurs au quotidien.
- **Analyste données** : transforme les chiffres en décisions.
- **Spécialiste cybersécurité** : protège les systèmes.
- **Formateur / médiateur numérique** : accompagnement aux usages.

## Citoyenneté numérique

Être citoyen numérique, c'est :

1. **Vérifier l'information** avant de la partager (sources fiables).
2. **Respecter les autres** : pas de harcèlement, pas d'insultes en ligne.
3. **Protéger ses données personnelles** (mot de passe fort, réglages de confidentialité).
4. **Respecter le droit d'auteur** : ne pas publier une œuvre sans autorisation.
5. **Signaler les contenus dangereux** ou illégaux.

## Le harcèlement en ligne

Le cyberharcèlement est puni par la loi dans la plupart des pays. Quelques réflexes :

- ne pas répondre ;
- conserver les preuves (captures d'écran) ;
- bloquer et signaler à la plateforme ;
- parler à un adulte de confiance ou à une autorité compétente.

> La technologie ne remplace pas le jugement humain : c'est vous qui décidez de ce que vous publiez et de ce que vous croyez.
"""),
        ],
        "exercise": {
            "title": "Quiz — Bases des TIC",
            "description": "Vérifiez votre compréhension des notions fondamentales.",
            "questions": [
                ("Que désigne l'acronyme TIC ?", ["Technologies de l'Information et de la Communication",
                                                  "Traitement Informatique des Communications",
                                                  "Techniques Intégrées de Cryptographie",
                                                  "Transmission Internet de Contenus"], 1,
                 "TIC = Technologies de l'Information et de la Communication."),
                ("Combien de bits contient un octet ?", ["4", "8", "16", "32"], 2,
                 "Un octet (byte) regroupe 8 bits."),
                ("Laquelle de ces propositions est une donnée numérique ?",
                 ["Une photo prise avec un téléphone", "Une idée non écrite", "Un souvenir", "Un sentiment"], 1,
                 "Une photo est codée en 0 et 1 : c'est une donnée numérique."),
                ("Le réseau mondial qui relie des milliards d'appareils s'appelle :",
                 ["Le Bluetooth", "Un intranet", "Internet", "Le Wi-Fi"], 3,
                 "Internet est le réseau des réseaux, à l'échelle mondiale."),
            ],
        },
    },
    {
        "title": "Informatique et composants d'un ordinateur",
        "category": "Fondamentaux",
        "level": "débutant",
        "estimated_minutes": 100,
        "summary": "Identifier le matériel, comprendre le rôle du processeur, de la mémoire et du stockage.",
        "description": "Découverte de l'architecture matérielle d'un ordinateur et des périphériques, avec des repères pour choisir un équipement.",
        "lessons": [
            ("Les composants internes", """## L'architecture de base

Un ordinateur repose sur le schéma **entrée → traitement → sortie**, complété par le stockage.

### Les composants essentiels

- **Carte mère** : la plaque qui relie tous les composants.
- **Processeur (CPU)** : exécute les instructions. Sa vitesse se mesure en GHz ; ses cœurs déterminent sa capacité à travailler en parallèle.
- **Mémoire vive (RAM)** : mémoire de travail très rapide, vidée à l'extinction. 8 Go est un minimum confortable aujourd'hui, 16 Go pour le montage vidéo.
- **Stockage** : disque dur (HDD, mécanique, lent mais économique) ou SSD (électronique, très rapide).
- **Alimentation** : fournit le courant électrique.
- **Carte graphique (GPU)** : affichage, jeux, calculs d'images et d'intelligence artificielle.

## Analogie du bureau

- Le **CPU** est le rédacteur.
- La **RAM** est la surface du bureau : plus elle est grande, plus on peut poser de documents en même temps.
- Le **stockage** est l'armoire : on y range tout, même quand on éteint.
- Le **GPU** est une équipe de dessinateurs travaillant en parallèle.

## Attention à l'électricité

Un ordinateur doit être branché sur une prise stable ; un **onduleur** protège contre les coupures brusques, qui peuvent corrompre des fichiers.
"""),
            ("Périphériques et connectique", """## Les périphériques

**Entrée** : clavier, souris, scanner, webcam, microphone, capteur d'empreinte.
**Sortie** : écran, imprimante, haut-parleurs, casque.
**Entrée/sortie** : écran tactile, clé USB, carte réseau, disque externe.

## Les ports et connexions

- **USB-A / USB-C** : périphériques, charge, transfert de données.
- **HDMI / DisplayPort** : écrans et projecteurs.
- **Jack 3,5 mm** : audio filaire.
- **Ethernet RJ45** : réseau filaire, plus stable que le Wi-Fi.
- **Bluetooth / Wi-Fi** : connexions sans fil.

## Bien choisir son matériel

| Usage | RAM conseillée | Stockage |
|---|---|---|
| Navigation, bureautique | 8 Go | 256 Go SSD |
| Études, programmation | 8–16 Go | 512 Go SSD |
| Montage vidéo, 3D | 16–32 Go | 1 To SSD |

> Un SSD améliore souvent plus le confort quotidien qu'un processeur plus puissant : le disque est le premier facteur de lenteur sur un ordinateur ancien.

## Entretien de base

- Nettoyer la poussière (surtout les ventilateurs).
- Éviter les chocs et les boissons près du clavier.
- Sauvegarder régulièrement sur un support externe.
"""),
            ("Le logiciel et le système d'exploitation", """## Matériel et logiciel

Le **matériel** (hardware) est physique ; le **logiciel** (software) est immatériel. Sans système d'exploitation, le matériel ne peut rien faire d'utile pour l'utilisateur.

## Les catégories de logiciels

- **Systèmes d'exploitation** : Windows, macOS, Linux, Android, iOS.
- **Logiciels applicatifs** : traitement de texte, tableur, navigateur.
- **Logiciels libres / propriétaires** : la différence porte sur la liberté d'étudier, modifier et redistribuer le code.
- **Logiciels malveillants** : virus, chevaux de Troie, rançongiciels — ce ne sont pas des "outils".

## Licences

Une licence définit ce que vous pouvez faire avec un logiciel : usage personnel, nombre de machines, revente interdite, etc. Utiliser un logiciel craqué, c'est s'exposer à des malwares et à des sanctions légales.

## Mises à jour

Une mise à jour corrige des bugs **et des failles de sécurité**. Repousser systématiquement les mises à jour revient à laisser une porte ouverte.
"""),
        ],
        "exercise": {
            "title": "Quiz — Matériel et logiciel",
            "description": "Testez vos connaissances sur les composants et le rôle du système.",
            "questions": [
                ("Quel composant perd son contenu lorsque l'ordinateur s'éteint ?",
                 ["Le SSD", "La mémoire vive (RAM)", "Le disque dur", "La carte mère"], 2,
                 "La RAM est volatile : elle se vide à l'extinction."),
                ("Quel périphérique est à la fois d'entrée et de sortie ?",
                 ["L'imprimante", "L'écran tactile", "Le scanner", "Le clavier"], 2,
                 "Un écran tactile reçoit le toucher (entrée) et affiche (sortie)."),
                ("Pourquoi installer les mises à jour de sécurité ?",
                 ["Pour occuper de l'espace disque", "Pour corriger des failles exploitées par les attaquants",
                  "Pour ralentir l'ordinateur", "Cela ne sert à rien"], 2,
                 "Les mises à jour colmatent des vulnérabilités connues."),
                ("Quel port réseau filaire est le plus courant ?",
                 ["HDMI", "USB-C", "RJ45", "Jack 3,5 mm"], 3, "Le connecteur RJ45 sert au câble Ethernet."),
            ],
        },
    },
    {
        "title": "Systèmes d'exploitation",
        "category": "Fondamentaux",
        "level": "débutant",
        "estimated_minutes": 80,
        "summary": "Gérer fichiers, dossiers, comptes utilisateurs et bonnes pratiques de maintenance.",
        "description": "Le système d'exploitation (OS) fait le lien entre l'utilisateur, les applications et le matériel.",
        "lessons": [
            ("Rôle du système d'exploitation", """## Définition

Le **système d'exploitation** est le logiciel principal de l'ordinateur. Il démarre la machine, gère le matériel et permet aux applications de fonctionner.

## Ses missions

1. **Gérer les fichiers** (créer, déplacer, supprimer).
2. **Gérer les processus** (programmes en cours d'exécution).
3. **Gérer les utilisateurs et droits** (comptes, mots de passe).
4. **Gérer le matériel** grâce aux pilotes (drivers).
5. **Assurer la sécurité de base** (isolation des applications, permissions).

## Les grands systèmes

- **Windows** : très répandu dans les bureaux et les écoles.
- **macOS** : environnement Apple, réputé pour la stabilité.
- **Linux** : libre, utilisé massivement sur les serveurs ; distributions : Ubuntu, Debian, Fedora.
- **Android / iOS** : systèmes mobiles.

> Un serveur qui héberge un site web tourne presque toujours sous Linux.
"""),
            ("Fichiers, dossiers et organisation", """## Arborescence

Les fichiers sont rangés dans une **arborescence** : un dossier racine contient des dossiers, qui contiennent des fichiers.

- Windows : `C:\\Utilisateurs\\Nom\\Documents`
- Linux / macOS : `/home/nom/Documents`

## Nommer proprement ses fichiers

- Éviter les espaces et les caractères spéciaux (`/ \\ : * ? " < > |`).
- Utiliser un format cohérent : `2026-03-rapport-tic.pdf`.
- Une **extension** indique le type : `.docx`, `.xlsx`, `.pdf`, `.jpg`, `.mp4`.

## Bonnes pratiques de rangement

```
Documents/
  Cours-TIC/
    01-Introduction/
      notes.md
      exercices.pdf
    02-Reseaux/
```

## Sauvegarde : la règle 3-2-1

- **3** copies de la donnée,
- sur **2** supports différents,
- dont **1** hors du site (cloud ou disque dans un autre lieu).

Un fichier unique sur un seul ordinateur n'est pas sauvegardé : il est simplement en sursis.

## Corbeille et effacement

Supprimer un fichier le place souvent dans la corbeille. Vider la corbeille le rend difficilement récupérable. Sur un SSD, la récupération est encore plus incertaine.
"""),
            ("Comptes utilisateurs et maintenance", """## Comptes et privilèges

Un ordinateur peut avoir plusieurs comptes :

- **Administrateur** : peut installer des logiciels et modifier le système.
- **Utilisateur standard** : usage quotidien, droits limités.

Bonne pratique : travailler avec un compte standard et n'utiliser l'administrateur que pour installer. Une erreur ou un malware aura alors moins d'impact.

## Le mot de passe de session

Choisissez un mot de passe long (une phrase de passe) et activez le verrouillage automatique après quelques minutes d'inactivité.

## Maintenance régulière

- Désinstaller les logiciels inutiles.
- Surveiller l'espace disque (garder au moins 15 % libre).
- Mettre à jour l'OS et les applications.
- Analyser avec un antivirus à jour.
- Redémarrer régulièrement (les mises à jour s'appliquent souvent au démarrage).

## Dépannage simple

1. Lire le message d'erreur.
2. Redémarrer.
3. Vérifier les mises à jour.
4. Chercher l'erreur exacte sur un site de support fiable.
5. Sauvegarder avant toute manipulation sensible.
"""),
        ],
        "exercise": {
            "title": "Quiz — Systèmes d'exploitation",
            "description": "Organisation des fichiers, comptes et maintenance.",
            "questions": [
                ("Quel système d'exploitation est le plus utilisé sur les serveurs web ?",
                 ["Windows 11", "Linux", "Android", "iOS"], 2, "La majorité des serveurs tournent sous Linux."),
                ("La règle de sauvegarde 3-2-1 signifie :",
                 ["3 fichiers, 2 dossiers, 1 clé USB", "3 copies, 2 supports, 1 hors site",
                  "3 sauvegardes par jour pendant 2 semaines", "3 utilisateurs, 2 administrateurs, 1 invité"], 2,
                 "Trois copies sur deux supports dont une externalisée."),
                ("Pourquoi travailler avec un compte utilisateur standard ?",
                 ["Pour aller plus vite", "Pour limiter l'impact d'une erreur ou d'un malware",
                  "Pour avoir plus d'espace disque", "Pour désactiver l'antivirus"], 2,
                 "Les droits limités réduisent la surface d'attaque."),
                ("Que faut-il faire avant une manipulation risquée du système ?",
                 ["Éteindre brutalement la machine", "Sauvegarder ses données", "Supprimer les pilotes", "Rien de particulier"], 2,
                 "La sauvegarde est le premier réflexe."),
            ],
        },
    },
    {
        "title": "Traitement de texte",
        "category": "Bureautique",
        "level": "débutant",
        "estimated_minutes": 90,
        "summary": "Rédiger, mettre en forme et exporter des documents professionnels.",
        "description": "Maîtriser les styles, la mise en page, les tableaux et l'export PDF avec Word, LibreOffice ou Google Docs.",
        "lessons": [
            ("De la saisie à la mise en forme", """## Les bases

Un traitement de texte sert à **rédiger** et **mettre en forme** des documents : lettre, rapport, mémoire, CV.

### Raccourcis indispensables

| Action | Windows/Linux | macOS |
|---|---|---|
| Copier | Ctrl+C | Cmd+C |
| Coller | Ctrl+V | Cmd+V |
| Annuler | Ctrl+Z | Cmd+Z |
| Rétablir | Ctrl+Y | Cmd+Shift+Z |
| Rechercher | Ctrl+F | Cmd+F |
| Enregistrer | Ctrl+S | Cmd+S |
| Mot en gras | Ctrl+B | Cmd+B |

## Les styles plutôt que le "manuel"

Au lieu de mettre chaque titre en 18 pt gras, utilisez les **styles** (Titre 1, Titre 2, Normal). Avantages :

- cohérence visuelle ;
- sommaire automatique ;
- modification globale instantanée ;
- accessibilité (lecteurs d'écran).

## Structurer un document

1. Page de titre.
2. Sommaire.
3. Introduction.
4. Développement en parties et sous-parties.
5. Conclusion.
6. Bibliographie / annexes.

> Règle d'or : **le fond d'abord, la forme ensuite**. On écrit, puis on met en forme.
"""),
            ("Mise en page et objets", """## Réglages de page

- **Marges** : 2 à 2,5 cm pour un document classique.
- **Orientation** : portrait (texte) ou paysage (tableaux larges).
- **En-tête / pied de page** : titre, numéro de page, date.
- **Numérotation** automatique : indispensable au-delà de 3 pages.

## Tableaux

Un tableau sert à comparer des données. Trois règles :

1. une seule idée par colonne ;
2. des entêtes clairs ;
3. des unités précisées (FCFA, %, kg).

## Images et légendes

Insérez des images de bonne qualité (au moins 150 dpi pour l'impression) et ajoutez une **légende** (« Figure 1 : ... »). Attention aux droits d'auteur : citez la source.

## Vérification orthographique

Activez la correction automatique, puis **relisez à voix haute**. Les correcteurs ne détectent pas les homophones (« a » / « à », « ou » / « où »).

## Export et compatibilité

- **PDF** : pour diffuser sans modifier la mise en page.
- **DOCX** : pour permettre la modification.
- Vérifiez le rendu du PDF avant envoi : polices, sauts de page, images.
"""),
            ("Documents professionnels et accessibilité", """## Une lettre administrative

Structure attendue :

```
Expéditeur (nom, adresse, contact)
Destinataire
Lieu et date
Objet : ...
Madame, Monsieur,

Corps de la lettre...

Formule de politesse.
Signature
```

## Un CV lisible

- Une page, deux au maximum.
- Un titre clair (« Développeur web junior »).
- Des expériences en **verbes d'action** : « conçu », « administré », « formé ».
- Des compétences vérifiables.
- Pas de photo obligatoire, pas d'informations discriminantes (âge, situation familiale).

## Accessibilité

- Contraste suffisant entre texte et fond.
- Police d'au moins 11–12 pt.
- Pas d'information portée uniquement par la couleur.
- Titres hiérarchisés pour les lecteurs d'écran.
- Texte alternatif sur les images.

## Enregistrer et nommer

Un nom de fichier professionnel : `2026-04-CV-Nom-Prenom.pdf`. Évitez `document final v3 vrai final.docx`.
"""),
        ],
        "exercise": {
            "title": "Quiz — Traitement de texte",
            "description": "Styles, mise en page et bonnes pratiques rédactionnelles.",
            "questions": [
                ("Pourquoi utiliser les styles de titres plutôt que la mise en forme manuelle ?",
                 ["Pour colorer le texte", "Pour générer un sommaire automatique et garder la cohérence",
                  "Pour imprimer plus vite", "Pour compresser le fichier"], 2,
                 "Les styles permettent sommaire automatique et cohérence globale."),
                ("Quel format privilégier pour diffuser un document non modifiable ?",
                 ["DOCX", "TXT", "PDF", "CSV"], 3, "Le PDF fige la mise en page."),
                ("Quel raccourci enregistre un document sous Windows ?",
                 ["Ctrl+P", "Ctrl+S", "Ctrl+E", "Ctrl+O"], 2, "Ctrl+S = Save (enregistrer)."),
                ("Un bon document accessible doit notamment :",
                 ["Utiliser uniquement des images", "Hiérarchiser les titres et soigner les contrastes",
                  "Éviter les tableaux", "Utiliser une police de 8 pt"], 2,
                 "La hiérarchie des titres et le contraste sont essentiels."),
            ],
        },
    },
    {
        "title": "Tableurs et présentations",
        "category": "Bureautique",
        "level": "intermédiaire",
        "estimated_minutes": 120,
        "summary": "Calculer avec Excel/LibreOffice Calc et concevoir des présentations efficaces.",
        "description": "Formules, fonctions, graphiques, tableaux croisés et règles de conception de diaporamas.",
        "lessons": [
            ("Formules et fonctions essentielles", """## La cellule, unité de base

Une feuille de calcul est une grille de cellules identifiées par une **colonne** et une **ligne** : `A1`, `B12`, `C3`.

Une formule commence toujours par `=` et peut contenir :

- des nombres : `=5+3`
- des références : `=A1+B1`
- des fonctions : `=SOMME(A1:A10)`

## Les fonctions à connaître

| Fonction | Rôle | Exemple |
|---|---|---|
| `SOMME` | additionner | `=SOMME(B2:B20)` |
| `MOYENNE` | moyenne | `=MOYENNE(C2:C20)` |
| `MAX` / `MIN` | extrêmes | `=MAX(D2:D50)` |
| `SI` | condition | `=SI(E2>=10;"Admis";"Ajourné")` |
| `NB.SI` | compter selon condition | `=NB.SI(B2:B50;"F")` |
| `RECHERCHEV` | croiser des tables | `=RECHERCHEV(A2;$H$2:$I$20;2;FAUX)` |

## Références relatives et absolues

- `A1` est **relative** : recopiée vers le bas, elle devient `A2`.
- `$A$1` est **absolue** : elle ne bouge jamais.

Le symbole `$` verrouille la référence. C'est indispensable dans les recherches et les barèmes.

## Les erreurs fréquentes

- `####` : colonne trop étroite.
- `#DIV/0!` : division par zéro.
- `#VALEUR!` : type de donnée incompatible.
- `#N/A` : valeur non trouvée dans une recherche.
"""),
            ("Graphiques et tableaux croisés", """## Choisir le bon graphique

- **Courbe** : évolution dans le temps.
- **Barres / colonnes** : comparaison de catégories.
- **Camembert** : répartition (peu de catégories, total = 100 %).
- **Nuage de points** : relation entre deux variables.

> Un graphique mal choisi désinforme, même avec des données exactes.

## Les 5 règles d'un graphique lisible

1. Un titre explicite.
2. Des axes nommés avec leurs unités.
3. Une échelle qui ne trompe pas (commencer à zéro pour des barres).
4. Pas plus de 5–6 couleurs.
5. La source des données.

## Tableau croisé dynamique (TCD)

Le TCD agrège automatiquement des milliers de lignes :

- **Lignes** : la catégorie à analyser (ex. classe).
- **Colonnes** : la seconde dimension (ex. sexe).
- **Valeurs** : ce que l'on mesure (ex. moyenne des notes).

Exemple : moyenne des notes par classe et par matière, en trois clics.

## Nettoyage des données

Avant tout calcul : une seule ligne d'entête, pas de cellules fusionnées, pas de lignes vides, une seule information par colonne.
"""),
            ("Présentations qui convainquent", """## Concevoir avant de projeter

Un diaporama **soutient** un discours, il ne le remplace pas.

## Règles de conception

- 1 idée par diapositive.
- 6 lignes maximum, 6 mots par ligne (règle 6×6, indicative).
- Police lisible (24 pt minimum pour le corps).
- Contraste élevé, fond sobre.
- Une image vaut mieux qu'un paragraphe.

## Structure type (10 minutes)

1. Accroche / problème.
2. Objectif.
3. Méthode.
4. Résultats.
5. Conclusion et appel à l'action.

## Erreurs classiques

- Lire ses diapositives mot pour mot.
- Surcharger de texte.
- Animations gadget.
- Orthographe non relue.
- Diapositives de secours oubliées pour les questions.

## Accessibilité et partage

Exportez en PDF pour éviter les problèmes de polices. Ajoutez un texte alternatif aux images. Vérifiez le rendu sur un vidéoprojecteur ou un téléphone avant la présentation.
"""),
        ],
        "exercise": {
            "title": "Quiz — Tableurs et présentations",
            "description": "Formules, graphiques et conception de diaporamas.",
            "questions": [
                ("Que signifie la référence `$B$2` dans une formule ?",
                 ["Une référence relative", "Une référence absolue", "Une erreur de syntaxe", "Une cellule vide"], 2,
                 "Les symboles $ verrouillent la ligne et la colonne."),
                ("Quelle fonction affiche une valeur selon une condition ?",
                 ["SOMME", "SI", "MOYENNE", "MAX"], 2, "La fonction SI teste une condition."),
                ("Quel graphique montre une évolution dans le temps ?",
                 ["Camembert", "Courbe", "Nuage de points", "Diagramme en secteurs"], 2,
                 "La courbe est adaptée aux séries temporelles."),
                ("Combien d'idées principales par diapositive ?",
                 ["Une", "Trois", "Cinq", "Autant que possible"], 1, "Une idée par diapositive."),
            ],
        },
    },
    {
        "title": "Internet et navigation Web",
        "category": "Internet & Web",
        "level": "débutant",
        "estimated_minutes": 90,
        "summary": "Comprendre le Web, évaluer la fiabilité des sources et naviguer en sécurité.",
        "description": "Fonctionnement d'Internet, URL, moteurs de recherche, Wi-Fi et vérification de l'information.",
        "lessons": [
            ("Comment fonctionne le Web", """## Internet et le Web

**Internet** est l'infrastructure mondiale de réseaux. Le **Web** est l'un des services qui circulent sur Internet (avec la messagerie, la visioconférence, etc.).

## Le modèle client-serveur

1. Vous saisissez une adresse dans le navigateur (**client**).
2. Une requête **HTTP/HTTPS** part vers un serveur identifié par son nom de domaine.
3. Le **DNS** traduit ce nom en adresse IP (comme un annuaire).
4. Le serveur répond avec une page (HTML, CSS, images).
5. Le navigateur affiche la page.

## Décoder une URL

```
https://ticmaster.example/cours/reseaux?page=2
└─┬─┘   └──────┬──────┘└────┬────┘└────┬────┘
protocole    domaine       chemin    paramètre
```

- **https** : version chiffrée de HTTP (le « s » = secure).
- Le **domaine** se lit de droite à gauche : `.example` (TLD), puis `ticmaster`.

## Le cadenas

Un cadenas signifie que la connexion est **chiffrée**, pas que le site est honnête. Un site d'arnaque peut aussi avoir un certificat valide.
"""),
            ("Rechercher et vérifier l'information", """## Bien formuler une recherche

- Utilisez des mots-clés précis, pas une phrase entière.
- Ajoutez des guillemets pour une expression exacte : `"sécurité informatique"`.
- Utilisez `site:` pour restreindre : `site:gov.mg taxes`.
- `-` pour exclure un mot : `javadoc -achat`.

## La méthode de vérification en 4 temps

1. **Qui ?** Qui est l'auteur ? Un organisme reconnu, un expert, un anonyme ?
2. **Quand ?** La date est-elle récente ? Une information de 2015 peut être obsolète.
3. **Où ?** Sur quel site est-elle publiée ? Site officiel, presse reconnue, blog ?
4. **Comment ?** Les sources sont-elles citées ? Le ton est-il sensationnaliste ?

## Croiser les sources

Une information solide apparaît dans **au moins deux sources indépendantes**. Les images peuvent être sorties de leur contexte : utilisez une recherche d'image inversée.

## Reconnaître une arnaque

- Promesse d'argent facile.
- Urgence (« votre compte sera supprimé dans 24 h »).
- Fautes d'orthographe et adresse bizarre (`secu-verification.xyz`).
- Demande de mot de passe par message.

> Règle simple : **aucun service sérieux ne demande votre mot de passe par e-mail**.
"""),
            ("Connexions et équipements", """## Wi-Fi

- Utilisez le protocole **WPA2/WPA3** et un mot de passe long.
- Évitez les réseaux publics non chiffrés pour les opérations sensibles ; si nécessaire, activez un **VPN**.
- Désactivez le partage automatique de fichiers sur les réseaux publics.

## Données mobiles

Attention aux quotas : la vidéo en haute définition consomme rapidement le forfait. Téléchargez en Wi-Fi, limitez les mises à jour automatiques en données mobiles.

## Navigateurs

- Mettez-le à jour (les failles sont corrigées).
- Utilisez des extensions minimales et vérifiées.
- Activez le bloqueur de suivi et le mode HTTPS uniquement.
- Vérifiez les permissions des sites (caméra, micro, notifications).

## Vie privée

Effacez régulièrement cookies et cache, mais retenez que cela ne vous rend pas anonyme. Les empreintes de navigateur (fingerprinting) existent aussi.
"""),
        ],
        "exercise": {
            "title": "Quiz — Internet et navigation",
            "description": "Fonctionnement du Web et esprit critique.",
            "questions": [
                ("Que signifie le « s » dans HTTPS ?",
                 ["Standard", "Secure (chiffré)", "Server", "Simple"], 2, "HTTPS = HTTP chiffré via TLS."),
                ("À quoi sert le DNS ?",
                 ["À chiffrer les mots de passe", "À traduire un nom de domaine en adresse IP",
                  "À bloquer les publicités", "À télécharger des fichiers"], 2,
                 "Le DNS est l'annuaire du Web."),
                ("Le cadenas dans le navigateur garantit que :",
                 ["Le site est honnête", "La connexion est chiffrée", "Le site est rapide", "Le site est public"], 2,
                 "Il certifie le chiffrement, pas l'honnêteté du site."),
                ("Quelle pratique renforce la fiabilité d'une information ?",
                 ["La partager vite", "Croiser plusieurs sources indépendantes",
                  "Se fier au nombre de likes", "Lire uniquement le titre"], 2,
                 "Le recoupement de sources est la base de la vérification."),
            ],
        },
    },
    {
        "title": "Courrier électronique et communication",
        "category": "Internet & Web",
        "level": "débutant",
        "estimated_minutes": 80,
        "summary": "Écrire des e-mails professionnels et se protéger du phishing.",
        "description": "Bonnes pratiques de rédaction, signature, pièces jointes, hameçonnage et outils collaboratifs.",
        "lessons": [
            ("Rédiger un e-mail professionnel", """## Structure

- **Objet** : court et explicite (« Demande de relevé — L1 Informatique »).
- **Formule d'appel** : « Bonjour Madame », « Bonjour Monsieur », « Bonjour l'équipe ».
- **Corps** : une idée principale, des phrases courtes, une demande claire.
- **Formule de politesse** et **signature**.

## Les 6 règles

1. Un objet précis.
2. Un destinataire unique (ou une liste justifiée).
3. Un message court : au-delà de 10 lignes, structurer avec des listes.
4. Pas de majuscules (cela signifie crier).
5. Relire avant d'envoyer.
6. Vérifier les pièces jointes **avant** de cliquer sur Envoyer.

## Le bouton « Répondre à tous »

Ne l'utilisez que si tous les destinataires ont besoin de la réponse. C'est l'erreur professionnelle la plus fréquente.

## Signature

```
Nom Prénom
Fonction — Organisation
Téléphone | Site web
```

Évitez les citations longues, les images lourdes et les couleurs flashy.
"""),
            ("Pièces jointes, stockage et outils collaboratifs", """## Pièces jointes

- Taille raisonnable (souvent 10–25 Mo maximum par message).
- Formats universels : PDF pour la lecture, DOCX/XLSX pour l'édition.
- Nommez clairement : `2026-05-rapport-stage-NomPrenom.pdf`.
- Un gros fichier se partage par lien (WeTransfer, Drive, OneDrive, Nextcloud).

## Le cloud

Le stockage en ligne synchronise un dossier entre appareils. Points de vigilance :

- vérifiez qui a accès au lien (public ou restreint) ;
- activez la double authentification sur le compte ;
- les données sensibles doivent être chiffrées ou rester en local ;
- lisez la politique de confidentialité si les données sont personnelles.

## Travail collaboratif

- Un seul document partagé plutôt que 12 copies par e-mail.
- Un nom de fichier avec une dernière date de mise à jour.
- Des commentaires plutôt que des modifications silencieuses.
- Gérer les droits : lecteur, commentateur, éditeur.
"""),
            ("Phishing et sécurité des comptes", """## Reconnaître un message frauduleux

Signaux d'alerte :

- expéditeur inconnu ou adresse légèrement modifiée (`support@banque-secure.net`) ;
- urgence et menace ;
- lien dont l'adresse réelle ne correspond pas au texte affiché ;
- pièce jointe inattendue (`.zip`, `.exe`, `.html`) ;
- demande d'informations confidentielles.

## Que faire ?

1. **Ne cliquez pas.**
2. Vérifiez l'expéditeur en affichant l'adresse complète.
3. Contactez l'organisme par un autre canal (téléphone officiel).
4. Signalez le message comme hameçonnage.
5. Si vous avez cliqué : changez le mot de passe depuis un appareil sain et prévenez l'administrateur.

## Protéger sa boîte

- Mot de passe unique et long.
- **Double authentification** (2FA) activée.
- Ne jamais réutiliser un mot de passe.
- Verrouillage de session sur les appareils partagés.
"""),
        ],
        "exercise": {
            "title": "Quiz — E-mail et communication",
            "description": "Rédaction professionnelle et lutte contre le phishing.",
            "questions": [
                ("Quel objet d'e-mail est le plus professionnel ?",
                 ["URGENT !!!", "Demande de relevé de notes — L1 Informatique",
                  "bonjour", "Question"], 2, "Un objet court, explicite et factuel."),
                ("Quel signe doit alerter dans un e-mail ?",
                 ["Une signature complète", "Une urgence soudaine avec menace",
                  "Un objet clair", "Un message court"], 2, "L'urgence est un levier classique d'arnaque."),
                ("Que faire d'un lien suspect reçu par e-mail ?",
                 ["Cliquer pour voir", "Ne pas cliquer et vérifier par un autre canal",
                  "Le transférer à tous ses contacts", "Répondre avec son mot de passe"], 2,
                 "On vérifie par un canal officiel indépendant."),
                ("Quelle pratique protège le mieux une boîte e-mail ?",
                 ["Le même mot de passe partout", "La double authentification",
                  "Un mot de passe de 6 caractères", "Désactiver les alertes"], 2,
                 "La 2FA bloque l'usage du mot de passe seul."),
            ],
        },
    },
    {
        "title": "Sécurité informatique",
        "category": "Sécurité & Réseaux",
        "level": "intermédiaire",
        "estimated_minutes": 110,
        "summary": "Menaces, mots de passe, rançongiciels, sauvegardes et hygiène numérique.",
        "description": "Module central : comprendre les attaques les plus courantes et appliquer les bonnes pratiques.",
        "lessons": [
            ("Les principales menaces", """## Panorama

- **Virus / ver** : se propage et perturbe le fonctionnement.
- **Cheval de Troie** : se cache dans un logiciel apparemment légitime.
- **Rançongiciel (ransomware)** : chiffre vos fichiers et exige une rançon.
- **Phishing** : trompe l'utilisateur pour voler des identifiants.
- **Ingénierie sociale** : manipule la personne plutôt que la machine.
- **Déni de service (DDoS)** : sature un service pour le rendre indisponible.
- **Attaque par force brute** : teste des milliers de mots de passe.

## Le facteur humain

La majorité des incidents commencent par un clic, un mot de passe faible ou une mise à jour repoussée. La sécurité est donc autant une **discipline humaine** qu'une technique.

## Le triangle de la sécurité (CIA)

- **Confidentialité** : seules les personnes autorisées accèdent à l'information.
- **Intégrité** : l'information n'est pas modifiée sans autorisation.
- **Disponibilité** : le service reste accessible.

Toute mesure de sécurité vise à protéger au moins l'un de ces trois piliers.
"""),
            ("Mots de passe et authentification", """## Construire un mot de passe robuste

- Longueur d'abord : **12 à 16 caractères minimum**.
- Une **phrase de passe** est plus facile à retenir : `Kely-Manga-2026-Tana!`.
- Jamais d'information personnelle (date de naissance, prénom).
- Un mot de passe **différent par service**.

## Le gestionnaire de mots de passe

Il génère et mémorise des mots de passe uniques. Vous ne retenez qu'une seule phrase de passe maîtresse. C'est la recommandation professionnelle.

## Double authentification (2FA)

Un second facteur : code temporaire, application d'authentification, clé physique. Le SMS est acceptable mais vulnérable au détournement de carte SIM ; les applications (TOTP) sont préférables.

## Hachage : ce que doit faire un site sérieux

Un site ne doit jamais stocker votre mot de passe. Il stocke une **empreinte** calculée avec un algorithme lent comme **Argon2id** ou bcrypt, complété d'un « sel » aléatoire. Même en cas de fuite de la base, les mots de passe restent difficiles à retrouver.

> Si un site vous envoie votre mot de passe en clair par e-mail, il ne le protège pas correctement.
"""),
            ("Réagir à un incident", """## Les réflexes en cas d'infection

1. **Déconnecter** l'appareil du réseau.
2. Ne pas payer de rançon : cela finance les attaquants et ne garantit rien.
3. Conserver les preuves (captures, messages).
4. Signaler à l'administrateur ou au responsable sécurité.
5. Restaurer depuis une **sauvegarde saine**.

## En cas de compromission de compte

1. Changer le mot de passe depuis un appareil non infecté.
2. Révoquer les sessions actives.
3. Vérifier les règles de transfert automatique dans la messagerie.
4. Prévenir ses contacts si des messages frauduleux ont été envoyés.
5. Activer la 2FA.

## Sauvegardes

La sauvegarde est la seule défense vraiment efficace contre un rançongiciel. Une sauvegarde **déconnectée** (hors ligne) est indispensable : un disque toujours branché sera chiffré aussi.

Testez la restauration au moins une fois : une sauvegarde jamais testée n'est pas une sauvegarde.
"""),
        ],
        "exercise": {
            "title": "Quiz — Sécurité informatique",
            "description": "Menaces, mots de passe et réaction aux incidents.",
            "questions": [
                ("Quel algorithme est recommandé pour stocker les mots de passe ?",
                 ["MD5", "SHA-1", "Argon2id", "Base64"], 3,
                 "Argon2id est conçu pour être lent et coûteux à attaquer."),
                ("Que fait un rançongiciel ?",
                 ["Il accélère l'ordinateur", "Il chiffre les fichiers et réclame une rançon",
                  "Il sauvegarde les données", "Il met à jour le système"], 2,
                 "Le ransomware chiffre les données et exige un paiement."),
                ("Quelle est la première action face à une infection ?",
                 ["Payer la rançon", "Déconnecter l'appareil du réseau", "Éteindre et jeter le disque",
                  "Envoyer ses fichiers par e-mail"], 2, "L'isolement limite la propagation."),
                ("Le principe de confidentialité garantit que :",
                 ["Les données sont toujours disponibles", "Seules les personnes autorisées accèdent aux données",
                  "Les données sont exactes", "Le service est rapide"], 2,
                 "La confidentialité restreint l'accès aux personnes habilitées."),
                ("Une sauvegarde efficace contre un ransomware doit être :",
                 ["Toujours connectée", "Déconnectée et testée", "Sur le même disque", "Chiffrée par le malware"], 2,
                 "Une copie hors ligne est indispensable."),
            ],
        },
    },
    {
        "title": "Réseaux informatiques",
        "category": "Sécurité & Réseaux",
        "level": "intermédiaire",
        "estimated_minutes": 100,
        "summary": "Adresses IP, LAN/WAN, routeurs, modèles et organisation d'un réseau d'établissement.",
        "description": "Comprendre comment les machines communiquent, se repèrent et se sécurisent.",
        "lessons": [
            ("Adresses IP et masques", """## Identifiants réseau

Chaque machine possède une **adresse IP**.

- **IPv4** : quatre nombres de 0 à 255 (`192.168.1.10`).
- **IPv6** : format long hexadécimal, conçu pour l'épuisement des adresses IPv4.

## Adresses privées

Réservées aux réseaux locaux :

- `10.0.0.0` – `10.255.255.255`
- `172.16.0.0` – `172.31.255.255`
- `192.168.0.0` – `192.168.255.255`

Un routeur fait la traduction entre ces adresses privées et Internet grâce au **NAT**.

## Masque de sous-réseau

`255.255.255.0` (= /24) signifie que les 3 premiers nombres identifient le réseau et le dernier identifie la machine.

Exemple : `192.168.1.10/24` et `192.168.1.25/24` sont dans le même réseau ; `192.168.2.10/24` n'y est pas.

## DHCP et DNS

- **DHCP** attribue automatiquement une IP.
- **DNS** associe un nom à une IP.
- **Passerelle** (gateway) est la sortie vers Internet.
"""),
            ("Types de réseaux et équipements", """## Échelles

- **PAN** : quelques mètres (Bluetooth).
- **LAN** : un bâtiment (école, bureau).
- **MAN** : une ville.
- **WAN** : un pays ou le monde (Internet).

## Équipements

- **Switch** : relie les machines d'un même réseau local.
- **Routeur** : relie des réseaux différents et choisit le chemin.
- **Point d'accès Wi-Fi** : étend le réseau sans fil.
- **Pare-feu (firewall)** : filtre le trafic entrant et sortant.
- **Modem** : convertit le signal de l'opérateur.

## Topologies

- **Étoile** : toutes les machines passent par un switch central (la plus courante).
- **Maillage** : redondance, coût élevé.
- **Bus** : ancienne, peu fiable.

## Câblage

Le câble **Ethernet catégorie 5e/6** supporte 1 Gbit/s sur 100 m. Pour de longues distances, la fibre optique est nécessaire.
"""),
            ("Sécuriser et diagnostiquer un réseau", """## Segments et VLAN

Séparer les usages limite la propagation d'une attaque :

- réseau administratif ;
- réseau des étudiants ;
- réseau des invités ;
- réseau des caméras / objets connectés.

## Wi-Fi sécurisé

- WPA2 ou WPA3, jamais WEP.
- Mot de passe long, différent de celui de l'administration du routeur.
- Désactiver WPS (vulnérable).
- SSID invité isolé, sans accès aux ressources internes.

## Diagnostic de base

```
ipconfig        (Windows) → adresse IP, passerelle
ip a            (Linux)   → interfaces réseau
ping 8.8.8.8    → test de connectivité
ping example.com → test DNS
tracert / traceroute → chemin suivi
nslookup example.com → résolution DNS
```

## Interpréter

- `ping` par IP fonctionne mais pas par nom → problème DNS.
- Aucun ping, même par IP → câble, Wi-Fi, passerelle ou pare-feu.
- Connexion lente sur tous les postes → saturation de la bande passante.
"""),
        ],
        "exercise": {
            "title": "Quiz — Réseaux",
            "description": "Adresses, équipements et diagnostics.",
            "questions": [
                ("Quelle adresse est privée ?",
                 ["8.8.8.8", "192.168.1.20", "41.207.10.5", "142.250.75.14"], 2,
                 "192.168.x.x fait partie des plages privées."),
                ("Quel équipement relie deux réseaux différents ?",
                 ["Le switch", "Le routeur", "Le répéteur", "Le hub"], 2, "Le routeur interconnecte des réseaux."),
                ("À quoi sert le DHCP ?",
                 ["Traduire les noms en IP", "Attribuer automatiquement des adresses IP",
                  "Chiffrer le trafic", "Bloquer les virus"], 2, "DHCP distribue la configuration réseau."),
                ("Un ping par IP fonctionne mais le nom du site est introuvable :",
                 ["Le câble est débranché", "Le DNS est mal configuré", "Le routeur est éteint", "Le site est payant"], 2,
                 "La résolution de noms est en cause."),
            ],
        },
    },
    {
        "title": "Programmation et développement Web",
        "category": "Développement",
        "level": "intermédiaire",
        "estimated_minutes": 150,
        "summary": "Premiers pas en HTML, CSS, JavaScript et Python, et logique algorithmique.",
        "description": "Construire une page web, comprendre la logique de programmation et les bases d'une API sécurisée.",
        "lessons": [
            ("Algorithmique et langages", """## Qu'est-ce qu'un algorithme ?

Une suite finie d'instructions qui transforme des **entrées** en **résultats**. Exemple : calculer une moyenne.

```
début
  lire les notes
  somme ← 0
  pour chaque note :
      somme ← somme + note
  moyenne ← somme / nombre_de_notes
  afficher moyenne
fin
```

## Les structures de contrôle

- **Séquence** : instructions les unes après les autres.
- **Condition** : `si ... alors ... sinon ...`
- **Boucle** : `répéter ...`, `pour i de 1 à 10`.

## Variables et types

Une variable est une boîte nommée contenant une valeur : entier, décimal, texte, booléen.

## Langages

- **Python** : lisible, idéal pour débuter, puissant pour les données et le serveur.
- **JavaScript** : le langage du navigateur, indispensable pour l'interactivité.
- **HTML/CSS** : structure et style d'une page (ce ne sont pas des langages de programmation au sens strict).

> Une erreur de syntaxe est une faute de frappe pour l'ordinateur : lire le message d'erreur, c'est déjà résoudre la moitié du problème.
"""),
            ("HTML, CSS et le Web", """## HTML : la structure

```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ma page</title>
</head>
<body>
  <header><h1>TIC MASTER</h1></header>
  <main>
    <p>Bienvenue sur la plateforme.</p>
    <a href="https://example.org">Un lien</a>
  </main>
</body>
</html>
```

Balises à connaître : `h1`–`h6` (titres), `p` (paragraphe), `ul`/`li` (listes), `a` (lien), `img` (image avec `alt`), `form`, `input`, `button`, `table`.

## CSS : la présentation

```css
:root { --bleu: #0b2a6f; }
body { font-family: system-ui, sans-serif; margin: 0; }
h1 { color: var(--bleu); }
.bouton { padding: .6rem 1rem; border-radius: 8px; background: #2563eb; color: #fff; }
```

## Responsive design

- Balise `viewport` dans l'entête.
- Unités relatives (`rem`, `%`, `vw`).
- **Flexbox** et **Grid** pour les mises en page.
- Points de rupture : 480 px (mobile), 768 px (tablette), 1024 px (ordinateur).

## Bonnes pratiques

Séparer HTML, CSS et JS. Valider le code. Tester sur un vrai téléphone.
"""),
            ("JavaScript, serveur et API sécurisée", """## JavaScript côté navigateur

```javascript
const bouton = document.querySelector("#envoyer");
bouton.addEventListener("click", async () => {
  const reponse = await fetch("/api/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": jeton },
    body: JSON.stringify({ body: "Bonjour" })
  });
  const data = await reponse.json();
  console.log(data);
});
```

## Le serveur

Un serveur reçoit des requêtes et renvoie des réponses. Avec Python, **Flask** permet de démarrer en quelques lignes :

```python
from flask import Flask, jsonify
app = Flask(__name__)

@app.get("/api/sante")
def sante():
    return jsonify({"status": "ok"})
```

## Une API, c'est un contrat

- **GET** : lire une ressource.
- **POST** : créer.
- **PUT/PATCH** : modifier.
- **DELETE** : supprimer.

## Sécurité côté serveur

Ne faites **jamais** confiance au navigateur :

1. Valider et filtrer toutes les entrées.
2. Vérifier les permissions à chaque requête.
3. Utiliser des requêtes paramétrées (anti-injection SQL).
4. Échapper les sorties HTML (anti-XSS).
5. Protéger les actions par un jeton CSRF.
6. Limiter le nombre de tentatives de connexion.

> Masquer un bouton dans l'interface n'est pas une sécurité : l'API doit refuser l'action.
"""),
        ],
        "exercise": {
            "title": "Quiz — Programmation web",
            "description": "Algorithmique, HTML/CSS et sécurité applicative.",
            "questions": [
                ("Quelle balise HTML définit le titre principal d'une page ?",
                 ["<title>", "<h1>", "<header>", "<strong>"], 2, "<h1> est le titre de niveau 1."),
                ("En CSS, quelle propriété rend une mise en page flexible en une dimension ?",
                 ["display: flex", "color", "margin", "font-size"], 1, "Flexbox gère une dimension."),
                ("Quelle méthode HTTP sert à créer une ressource ?",
                 ["GET", "POST", "DELETE", "HEAD"], 2, "POST crée une ressource."),
                ("Pourquoi le contrôle des permissions doit-il être fait côté serveur ?",
                 ["Parce que c'est plus joli", "Parce que le navigateur peut être contourné par l'utilisateur",
                  "Pour économiser la batterie", "Pour accélérer le CSS"], 2,
                 "Le client est contrôlé par l'utilisateur : seule la vérification serveur protège."),
                ("Quelle pratique protège contre l'injection SQL ?",
                 ["Concaténer les chaînes", "Utiliser des requêtes paramétrées", "Désactiver les logs", "Chiffrer le HTML"], 2,
                 "Les requêtes paramétrées séparent code et données."),
            ],
        },
    },
    {
        "title": "Intelligence artificielle",
        "category": "Intelligence Artificielle",
        "level": "intermédiaire",
        "estimated_minutes": 100,
        "summary": "Comprendre les principes de l'IA, ses usages, ses limites et l'éthique associée.",
        "description": "De la donnée à la décision : apprendre ce qu'un modèle apprend, ce qu'il ne comprend pas et comment l'utiliser de façon responsable.",
        "lessons": [
            ("Qu'est-ce que l'intelligence artificielle ?", """## Définition

L'**intelligence artificielle** regroupe les techniques permettant à une machine d'accomplir des tâches qui requièrent habituellement l'intelligence humaine : reconnaître une image, traduire, résumer, prédire.

## Apprentissage supervisé

On fournit des **exemples étiquetés** :

- entrée : photo de feuille ; étiquette : « manguier » ou « riz » ;
- le modèle ajuste ses paramètres pour réduire ses erreurs ;
- il généralise ensuite sur de nouvelles photos.

## Les autres familles

- **Apprentissage non supervisé** : regrouper des données sans étiquettes (segmentation clients).
- **Apprentissage par renforcement** : apprendre par essais et récompenses.
- **IA générative** : produire du texte, des images, du code à partir de motifs appris.

## Ce que l'IA n'est pas

Un modèle n'a pas de compréhension du monde ni d'intention. Il calcule des probabilités sur des motifs. Il peut donc produire des réponses **plausibles mais fausses** ("hallucinations").
"""),
            ("Données, biais et qualité", """## La donnée est le carburant

Sans données de qualité, pas de modèle fiable. Trois problèmes fréquents :

1. **Données insuffisantes** : le modèle ne généralise pas.
2. **Données biaisées** : si les exemples ne représentent qu'une partie de la population, les décisions seront injustes.
3. **Données erronées ou obsolètes** : le modèle apprend des erreurs.

## Biais réel

Un système de recrutement entraîné sur des embauches passées reproduira les déséquilibres passés. Ce n'est pas la machine qui est sexiste : ce sont les données.

## Protection des données personnelles

- Minimiser la collecte.
- Anonymiser si possible.
- Informer les personnes.
- Respecter la réglementation locale sur la protection des données.

## Évaluer un modèle

- **Précision** : proportion de bonnes réponses.
- **Rappel** : capacité à retrouver tous les cas positifs.
- **Robustesse** : comportement face aux cas inattendus.

> Une exactitude de 95 % ne signifie rien si les 5 % d'erreurs concernent les décisions les plus graves.
"""),
            ("Usages responsables et prompt engineering", """## Bien écrire une consigne (prompt)

Un bon prompt précise :

- le **rôle** attendu (« Tu es un professeur de TIC ») ;
- le **contexte** (« pour des débutants à Antananarivo ») ;
- la **tâche** (« explique la différence entre RAM et stockage ») ;
- le **format** (« en 5 puces, avec un exemple ») ;
- les **contraintes** (« sans jargon, en français »).

## Vérifier systématiquement

- Les faits, les chiffres et les sources.
- Le code exécuté avant de l'utiliser.
- Les références (les modèles inventent parfois des citations).

## Usages utiles en éducation

- reformuler une notion difficile ;
- générer des exercices supplémentaires ;
- corriger l'orthographe ;
- traduire ;
- expliquer une erreur de code.

## Usages à éviter

- Faire rédiger à sa place un devoir évalué.
- Publier des données personnelles dans un outil grand public.
- Décider seul d'une orientation ou d'une sanction sur la base d'un score automatique.

## Transparence

Indiquez quand une IA a été utilisée. L'utilisateur a le droit de savoir à qui il parle, et un humain reste responsable de la décision finale.
"""),
        ],
        "exercise": {
            "title": "Quiz — Intelligence artificielle",
            "description": "Principes, biais et usage responsable.",
            "questions": [
                ("En apprentissage supervisé, le modèle apprend à partir de :",
                 ["Données sans étiquettes", "Exemples étiquetés", "Règles écrites à la main", "Hasard pur"], 2,
                 "L'apprentissage supervisé s'appuie sur des exemples étiquetés."),
                ("Un « biais » dans un modèle vient souvent :",
                 ["De la vitesse du processeur", "Des données d'entraînement déséquilibrées",
                  "De la couleur de l'interface", "Du nombre de câbles"], 2,
                 "Les données reflètent et amplifient les déséquilibres."),
                ("Une « hallucination » d'IA désigne :",
                 ["Une image floue", "Une réponse plausible mais fausse", "Un bug d'affichage", "Une panne réseau"], 2,
                 "Le modèle génère une information inventée mais crédible."),
                ("Quel est le bon réflexe face à une réponse d'IA ?",
                 ["La publier telle quelle", "Vérifier les faits et les sources", "La traduire en anglais", "L'ignorer toujours"], 2,
                 "La vérification humaine reste indispensable."),
            ],
        },
    },
    {
        "title": "Exercices pratiques et évaluations",
        "category": "Fondamentaux",
        "level": "intermédiaire",
        "estimated_minutes": 120,
        "summary": "Mettre en pratique : ateliers bureautiques, recherche d'information, sécurité et mini-projet.",
        "description": "Ce module propose des travaux pratiques corrigés qui mobilisent l'ensemble du programme.",
        "lessons": [
            ("Atelier 1 — Dossier professionnel", """## Objectif

Produire un dossier complet de 2 à 3 pages sur un thème TIC de votre choix, en respectant une charte de mise en forme.

## Consignes

1. **Choisir un thème** : « La sécurité des données personnelles », « L'usage du mobile money », « L'IA dans l'éducation »...
2. **Structure imposée** : page de titre, sommaire automatique, introduction (10 lignes), deux parties, conclusion, sources.
3. **Mise en forme** : styles de titres, police 12 pt, interligne 1,15, marges 2,5 cm, numérotation des pages.
4. **Contenu** : au moins 3 sources citées, 1 tableau et 1 illustration légendée.
5. **Export** : PDF + DOCX.

## Grille d'évaluation (20 points)

| Critère | Points |
|---|---|
| Respect de la structure | 4 |
| Qualité de la mise en forme | 4 |
| Pertinence du contenu | 6 |
| Sources citées et vérifiables | 3 |
| Orthographe et lisibilité | 3 |

## Conseil

Écrivez d'abord tout le texte au brouillon, sans mise en forme. La mise en page vient toujours après.
"""),
            ("Atelier 2 — Tableau de bord de notes", """## Objectif

Créer un classeur qui calcule automatiquement les moyennes d'une classe.

## Données d'exemple

| Nom | Devoir 1 | Devoir 2 | Examen |
|---|---|---|---|
| Rakoto | 12 | 15 | 13 |
| Rasoa | 8 | 11 | 9 |
| Andry | 16 | 14 | 17 |
| Hery | 6 | 9 | 8 |

## Travail demandé

1. Calculer la moyenne de chaque étudiant : `=(B2*0,3)+(C2*0,3)+(D2*0,4)`.
2. Afficher « Admis » si la moyenne ≥ 10, sinon « Ajourné » avec `SI`.
3. Calculer la moyenne de la classe, la note maximale et minimale.
4. Compter le nombre d'admis avec `NB.SI`.
5. Créer un graphique en colonnes comparant les étudiants.
6. Mettre en forme conditionnelle : rouge sous 10, vert au-dessus de 15.

## Pièges à éviter

- Les cellules fusionnées.
- Les pourcentages tapés en texte (« 30 % » au lieu de 0,3).
- Les formules recopiées sans vérifier les `$`.

## Livrable

Un fichier `.xlsx` nommé `notes-classe-2026.xlsx`, avec une feuille « Saisie » et une feuille « Synthèse ».
"""),
            ("Atelier 3 — Audit de sécurité personnel", """## Objectif

Auditer vos propres pratiques numériques et produire un plan d'action.

## Grille d'auto-évaluation

| Question | Oui / Non |
|---|---|
| Mes mots de passe sont-ils uniques par service ? | |
| Ai-je activé la double authentification ? | |
| Mes sauvegardes sont-elles testées et hors ligne ? | |
| Mon système est-il à jour ? | |
| Suis-je capable de reconnaître un phishing ? | |
| Mes réseaux sociaux sont-ils restreints ? | |
| Ai-je vérifié les permissions de mes applications mobiles ? | |

## Travail demandé

1. Remplir honnêtement la grille.
2. Identifier les 3 faiblesses les plus importantes.
3. Proposer une action corrective mesurable pour chacune, avec une date.
4. Rédiger un court rapport (1 page) avec un tableau avant/après.

## Exemple de plan d'action

| Faiblesse | Action | Échéance |
|---|---|---|
| Mots de passe réutilisés | Installer un gestionnaire de mots de passe | Semaine 1 |
| Pas de 2FA | Activer la 2FA sur la messagerie | Semaine 1 |
| Aucune sauvegarde | Disque externe + copie mensuelle | Semaine 2 |

> La sécurité n'est pas un état, c'est une habitude. Un petit pas chaque semaine vaut mieux qu'une réforme intenable.
"""),
        ],
        "exercise": {
            "title": "Évaluation pratique — Méthode",
            "description": "Vérifiez votre maîtrise de la démarche de projet.",
            "questions": [
                ("Dans l'atelier de dossier professionnel, quelle est la première étape ?",
                 ["Choisir la police", "Rédiger le contenu au brouillon", "Insérer des images", "Créer le sommaire"], 2,
                 "Le fond d'abord, la forme ensuite."),
                ("Quelle formule calcule une moyenne pondérée ?",
                 ["=SOMME(B2:D2)", "=(B2*0,3)+(C2*0,3)+(D2*0,4)", "=MOYENNE(B2)", "=SI(B2>10)"] , 2,
                 "Chaque note est multipliée par son coefficient."),
                ("Que signifie tester une sauvegarde ?",
                 ["Compter les fichiers", "Restaurer réellement des données pour vérifier",
                  "Acheter un disque", "La chiffrer"], 2, "Seule une restauration réelle prouve l'efficacité."),
                ("Un plan d'action de sécurité doit être :", 
                 ["Vague et long", "Mesurable avec une échéance", "Secret", "Sans priorité"], 2,
                 "Une action mesurable et datée est suivie et évaluée."),
            ],
        },
    },
]


EXAMS = [
    {
        "title": "Examen trimestriel T1 — Fondamentaux des TIC",
        "term": "T1",
        "duration_minutes": 20,
        "pass_score": 50,
        "description": "Modules 1 à 3 : introduction aux TIC, composants, systèmes d'exploitation.",
        "questions": [
            ("Quel est le rôle principal du système d'exploitation ?",
             ["Créer des sites web", "Gérer le matériel et les applications", "Compresser les fichiers", "Chiffrer le disque"],
             2, "L'OS fait le lien entre matériel, logiciels et utilisateur."),
            ("La RAM est une mémoire :", ["Permanente", "Volatile", "Optique", "Externe"], 2,
             "Elle perd son contenu à l'extinction."),
            ("Un SSD se distingue du disque dur par :",
             ["Sa capacité toujours plus faible", "L'absence de pièces mécaniques", "Son prix plus élevé uniquement",
              "Son incompatibilité avec Windows"], 2, "Le SSD est électronique, donc plus rapide."),
            ("TIC signifie :", ["Technologies de l'Information et de la Communication", "Technique Informatique de Codage",
                                "Transfert Intégral de Connaissances", "Traitement Intelligent des Communications"], 1,
             "Définition de référence."),
            ("Lequel n'est PAS un système d'exploitation ?", ["Linux", "Windows", "macOS", "Firefox"], 4,
             "Firefox est un navigateur."),
            ("Un octet vaut :", ["2 bits", "4 bits", "8 bits", "16 bits"], 3, "1 octet = 8 bits."),
        ],
    },
    {
        "title": "Examen trimestriel T2 — Bureautique et Internet",
        "term": "T2",
        "duration_minutes": 20,
        "pass_score": 50,
        "description": "Modules 4 à 6 : traitement de texte, tableurs et présentations, Internet.",
        "questions": [
            ("Pourquoi utiliser les styles dans un traitement de texte ?",
             ["Pour imprimer en couleur", "Pour la cohérence et le sommaire automatique",
              "Pour réduire la taille du fichier", "Pour partager en ligne"], 2, "Les styles structurent le document."),
            ("Dans un tableur, `$A$1` est une référence :", ["Relative", "Absolue", "Erronée", "Circulaire"], 2,
             "Les $ verrouillent la référence."),
            ("Quel graphique compare des catégories ?", ["Courbe", "Barres/colonnes", "Nuage de points", "Radar"], 2,
             "Les barres comparent des catégories."),
            ("HTTPS garantit :", ["L'honnêteté du site", "Le chiffrement de la connexion", "La gratuité", "L'absence de virus"], 2,
             "HTTPS chiffre les échanges."),
            ("Le DNS sert à :", ["Chiffrer les e-mails", "Traduire un nom de domaine en adresse IP",
                                 "Bloquer les publicités", "Accélérer le Wi-Fi"], 2, "C'est l'annuaire d'Internet."),
            ("Une règle de présentation efficace est :", ["Une idée par diapositive", "10 polices différentes",
                                                           "Un maximum de texte", "Lire ses notes mot à mot"], 1,
             "Une idée par diapositive."),
        ],
    },
    {
        "title": "Examen trimestriel T3 — Sécurité, réseaux, IA et développement",
        "term": "T3",
        "duration_minutes": 25,
        "pass_score": 50,
        "description": "Modules 7 à 11 : sécurité, réseaux, programmation web, intelligence artificielle.",
        "questions": [
            ("Argon2id est utilisé pour :", ["Compresser les images", "Hacher les mots de passe",
                                             "Router les paquets", "Afficher les pages"], 2,
             "C'est un algorithme de hachage lent et salé."),
            ("Une adresse IP privée commence par :", ["8.8", "192.168", "142.250", "41.207"], 2,
             "192.168.0.0/16 est une plage privée."),
            ("Quelle méthode HTTP crée une ressource ?", ["GET", "POST", "HEAD", "TRACE"], 2, "POST crée."),
            ("Le CSRF protège contre :",
             ["Les requêtes forgées depuis un autre site", "Les coupures de courant",
              "Les virus USB", "Le spam téléphonique"], 1, "Le jeton CSRF empêche la soumission forgée."),
            ("Un modèle d'IA qui invente une réponse crédible commet :",
             ["Une hallucination", "Une injection SQL", "Un déni de service", "Un timeout"], 1,
             "On parle d'hallucination."),
            ("La règle 3-2-1 concerne :", ["Le Wi-Fi", "Les sauvegardes", "Les mots de passe", "Les câbles réseau"], 2,
             "Trois copies, deux supports, une hors site."),
            ("Quel est le premier réflexe en cas de phishing reçu ?",
             ["Cliquer pour vérifier", "Ne pas cliquer et signaler", "Répondre avec ses identifiants",
              "Transférer à tout le monde"], 2, "On ne clique pas et on signale."),
        ],
    },
]

ANNOUNCEMENTS = [
    ("Bienvenue sur TIC MASTER",
     "La plateforme de formation aux TIC est ouverte. Votre compte a été créé par l'administration : "
     "pensez à modifier votre mot de passe lors de votre première connexion. Bon apprentissage !",
     True),
    ("Calendrier des examens trimestriels",
     "Les examens T1, T2 et T3 sont disponibles dans l'onglet « Examen trimestriel ». "
     "Attention : quitter l'onglet pendant un examen est considéré comme une tentative de fraude et entraîne l'élimination immédiate.",
     True),
    ("Règles de sécurité",
     "Ne partagez jamais votre mot de passe. Toute demande d'identifiants par message est frauduleuse : "
     "signalez-la à l'administrateur via la messagerie interne.",
     True),
]
