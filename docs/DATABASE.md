# Schéma de la base de données — TIC MASTER

Moteur : **SQLite** en local (`instance/ticmaster.db`), **PostgreSQL** en production.
ORM : SQLAlchemy 2 / Flask-SQLAlchemy 3. Les clés étrangères utilisent `ON DELETE CASCADE`
pour les données dépendantes et `SET NULL` pour les références facultatives (auteur supprimé).

## Vue d'ensemble

```
users ──┬── auth_sessions        (sessions serveur révocables)
        ├── lesson_progress ──── lessons ──── modules ──── categories
        ├── attempts ─── answers ─── questions ─── options
        │        └── exercises
        ├── messages (expéditeur / destinataire)
        ├── battle_members ──── battle_rooms
        ├── audit_logs
        └── password_reset_requests

announcements · resources · settings
```

## Relations principales

| Relation | Cardinalité | Règle |
|---|---|---|
| `users` → `auth_sessions` | 1—N | suppression en cascade |
| `users` → `attempts` | 1—N | une tentative = un utilisateur, une évaluation |
| `attempts` → `answers` | 1—N | une seule réponse par question (contrainte unique) |
| `exercises` → `questions` → `options` | 1—N—N | une seule option correcte par question |
| `modules` → `lessons` / `resources` / `exercises` | 1—N | cascade |
| `users` → `lesson_progress` → `lessons` | 1—N | contrainte unique (user, lesson) |
| `battle_rooms` → `battle_members` | 1—N | contrainte unique (room, user) |

## Index

Index automatiques sur les clés primaires, plus :

- `users.username` (unique), `users.email` (unique), `users.role`, `users.status`
- `auth_sessions.token_hash` (unique), `auth_sessions.user_id`
- `modules.slug` (unique), `modules.status`
- `lessons.module_id`, `lesson_progress.user_id`, `lesson_progress.lesson_id`
- `exercises.kind`, `questions.exercise_id`, `options.question_id`
- `attempts.user_id`, `attempts.exercise_id`, `attempts.status`
- `messages.room`, `messages.created_at`, `messages.sender_id`
- `battle_rooms.code` (unique)
- `audit_logs.action`, `audit_logs.created_at`, `audit_logs.actor_id`

## Dictionnaire des tables

Toutes les dates sont stockées en **UTC** (datetime naïf, compatible SQLite et PostgreSQL) et
converties à l'affichage.

### `categories`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `name` | VARCHAR(120) | UNIQUE, NOT NULL |
| `slug` | VARCHAR(140) | UNIQUE, NOT NULL, INDEX |
| `description` | TEXT | — |
| `icon` | VARCHAR(40) | — |
| `order_index` | INTEGER | — |

### `settings`

| Colonne | Type | Contraintes |
|---|---|---|
| `key` | VARCHAR(80) | PK, NOT NULL |
| `value` | TEXT | — |

### `users`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `username` | VARCHAR(64) | UNIQUE, NOT NULL, INDEX |
| `email` | VARCHAR(190) | UNIQUE, INDEX |
| `full_name` | VARCHAR(160) | NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `role` | VARCHAR(20) | NOT NULL, INDEX |
| `status` | VARCHAR(20) | NOT NULL, INDEX |
| `must_change_password` | BOOLEAN | NOT NULL |
| `bio` | TEXT | NOT NULL |
| `avatar_color` | VARCHAR(16) | NOT NULL |
| `created_at` | DATETIME | NOT NULL |
| `last_login_at` | DATETIME | — |
| `last_seen_at` | DATETIME | — |
| `password_changed_at` | DATETIME | — |
| `failed_attempts` | INTEGER | NOT NULL |
| `locked_until` | DATETIME | — |

### `announcements`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `title` | VARCHAR(190) | NOT NULL |
| `body` | TEXT | NOT NULL |
| `published` | BOOLEAN | NOT NULL |
| `created_by` | INTEGER | FK → `users.id` |
| `created_at` | DATETIME | INDEX |

### `audit_logs`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `actor_id` | INTEGER | FK → `users.id`, INDEX |
| `actor_label` | VARCHAR(120) | NOT NULL |
| `action` | VARCHAR(80) | NOT NULL, INDEX |
| `target` | VARCHAR(190) | — |
| `details` | TEXT | — |
| `ip` | VARCHAR(64) | — |
| `created_at` | DATETIME | NOT NULL, INDEX |

### `auth_sessions`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `token_hash` | VARCHAR(64) | UNIQUE, NOT NULL, INDEX |
| `created_at` | DATETIME | NOT NULL |
| `last_seen_at` | DATETIME | NOT NULL |
| `expires_at` | DATETIME | NOT NULL |
| `revoked_at` | DATETIME | — |
| `ip` | VARCHAR(64) | — |
| `user_agent` | VARCHAR(255) | — |

### `battle_rooms`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `name` | VARCHAR(120) | NOT NULL |
| `mode` | VARCHAR(20) | NOT NULL |
| `code` | VARCHAR(10) | UNIQUE, NOT NULL, INDEX |
| `owner_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `status` | VARCHAR(20) | — |
| `current_index` | INTEGER | — |
| `question_count` | INTEGER | — |
| `question_ids` | TEXT | — |
| `question_started_at` | DATETIME | — |
| `created_at` | DATETIME | — |
| `finished_at` | DATETIME | — |

### `messages`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `sender_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `room` | VARCHAR(60) | NOT NULL, INDEX |
| `recipient_id` | INTEGER | FK → `users.id` |
| `body` | TEXT | NOT NULL |
| `created_at` | DATETIME | INDEX |
| `deleted` | BOOLEAN | NOT NULL |

### `modules`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `title` | VARCHAR(190) | NOT NULL |
| `slug` | VARCHAR(200) | UNIQUE, NOT NULL, INDEX |
| `summary` | TEXT | — |
| `description` | TEXT | — |
| `image_url` | VARCHAR(400) | — |
| `icon` | VARCHAR(40) | — |
| `category_id` | INTEGER | FK → `categories.id`, INDEX |
| `level` | VARCHAR(20) | — |
| `order_index` | INTEGER | — |
| `status` | VARCHAR(20) | INDEX |
| `estimated_minutes` | INTEGER | — |
| `created_by` | INTEGER | FK → `users.id` |
| `created_at` | DATETIME | — |
| `updated_at` | DATETIME | — |

### `password_reset_requests`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `status` | VARCHAR(20) | NOT NULL |
| `token_hash` | VARCHAR(64) | UNIQUE |
| `expires_at` | DATETIME | — |
| `created_at` | DATETIME | NOT NULL |
| `handled_by` | INTEGER | FK → `users.id` |
| `note` | VARCHAR(255) | — |

### `battle_members`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `room_id` | INTEGER | FK → `battle_rooms.id`, NOT NULL, INDEX |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `score` | INTEGER | — |
| `answered_index` | INTEGER | — |
| `last_answer_correct` | BOOLEAN | — |
| `joined_at` | DATETIME | — |

### `exercises`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `module_id` | INTEGER | FK → `modules.id`, INDEX |
| `title` | VARCHAR(190) | NOT NULL |
| `description` | TEXT | — |
| `kind` | VARCHAR(20) | INDEX |
| `term` | VARCHAR(30) | — |
| `duration_minutes` | INTEGER | — |
| `pass_score` | INTEGER | — |
| `max_tab_violations` | INTEGER | — |
| `published` | BOOLEAN | NOT NULL |
| `created_by` | INTEGER | FK → `users.id` |
| `created_at` | DATETIME | — |

### `lessons`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `module_id` | INTEGER | FK → `modules.id`, NOT NULL, INDEX |
| `title` | VARCHAR(190) | NOT NULL |
| `content` | TEXT | — |
| `image_url` | VARCHAR(400) | — |
| `video_url` | VARCHAR(400) | — |
| `document_url` | VARCHAR(400) | — |
| `order_index` | INTEGER | — |
| `estimated_minutes` | INTEGER | — |
| `published` | BOOLEAN | NOT NULL |
| `created_at` | DATETIME | — |

### `resources`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `module_id` | INTEGER | FK → `modules.id`, NOT NULL, INDEX |
| `title` | VARCHAR(190) | NOT NULL |
| `url` | VARCHAR(400) | — |
| `filename` | VARCHAR(255) | — |
| `size` | INTEGER | — |
| `created_at` | DATETIME | — |

### `attempts`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `exercise_id` | INTEGER | FK → `exercises.id`, NOT NULL, INDEX |
| `started_at` | DATETIME | NOT NULL |
| `submitted_at` | DATETIME | — |
| `score` | INTEGER | — |
| `max_score` | INTEGER | — |
| `status` | VARCHAR(20) | INDEX |
| `tab_violations` | INTEGER | — |
| `elimination_reason` | VARCHAR(255) | — |
| `last_heartbeat` | DATETIME | — |
| `reset_by` | INTEGER | FK → `users.id` |
| `reset_at` | DATETIME | — |

### `lesson_progress`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `user_id` | INTEGER | FK → `users.id`, NOT NULL, INDEX |
| `lesson_id` | INTEGER | FK → `lessons.id`, NOT NULL, INDEX |
| `completed_at` | DATETIME | — |

### `questions`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `exercise_id` | INTEGER | FK → `exercises.id`, NOT NULL, INDEX |
| `text` | TEXT | NOT NULL |
| `explanation` | TEXT | — |
| `points` | INTEGER | — |
| `order_index` | INTEGER | — |

### `options`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `question_id` | INTEGER | FK → `questions.id`, NOT NULL, INDEX |
| `text` | VARCHAR(400) | NOT NULL |
| `is_correct` | BOOLEAN | NOT NULL |
| `order_index` | INTEGER | — |

### `answers`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | INTEGER | PK, NOT NULL |
| `attempt_id` | INTEGER | FK → `attempts.id`, NOT NULL, INDEX |
| `question_id` | INTEGER | FK → `questions.id`, NOT NULL |
| `option_id` | INTEGER | FK → `options.id` |
| `is_correct` | BOOLEAN | — |
| `points_awarded` | INTEGER | — |
| `answered_at` | DATETIME | — |

## Notes de conception

1. **Aucun mot de passe en clair** : `users.password_hash` contient une empreinte Argon2id
   (`$argon2id$…`), ou scrypt si la bibliothèque n'est pas disponible.
2. **Jetons de session** : `auth_sessions.token_hash` stocke le **SHA-256** du jeton envoyé au
   client. Une fuite de base ne permet donc pas de rejouer une session.
3. **Jetons de réinitialisation** : même principe (`password_reset_requests.token_hash`),
   validité 24 h, usage unique (`status = used`).
4. **Progression** : `lesson_progress` ne conserve que les leçons terminées (présence = terminée).
   Les pourcentages sont calculés à la volée sur les leçons publiées.
5. **Anti-fraude** : `attempts.status` ∈ `in_progress | submitted | eliminated`,
   `attempts.tab_violations`, `attempts.elimination_reason`, `attempts.reset_by` / `reset_at`
   (traçabilité de la réaffectation par le super administrateur).
6. **Conservation des données** : lors de la suppression d'un compte, `audit_logs.actor_id` est
   mis à `NULL` (le libellé `actor_label` est conservé pour l'audit) et les messages envoyés sont
   remplacés par « [message supprimé] » puis marqués supprimés.

## Sauvegarde et restauration

```bash
# PostgreSQL
pg_dump "$DATABASE_URL" -Fc -f backup-$(date +%F).dump
pg_restore -d "$DATABASE_URL" --clean backup-2026-01-01.dump

# SQLite
sqlite3 instance/ticmaster.db ".backup backup.db"
```

## Migration vers PostgreSQL

1. Renseigner `DATABASE_URL` (format `postgresql://user:password@host/db`).
2. `python seed.py init` puis `python seed.py superadmin` puis `python seed.py seed`.
3. Aucune modification de code n'est nécessaire : les types utilisés (`String`, `Text`, `Integer`,
   `Boolean`, `DateTime`) sont portables.
4. Pour les évolutions de schéma ultérieures, ajouter **Alembic** (`flask db init/migrate/upgrade`).
