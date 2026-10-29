# -*- coding: utf-8 -*-
"""Modèles de données — TIC MASTER."""
from datetime import datetime, timezone, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .security.hashing import hash_password, verify_password, needs_rehash

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER)
ROLE_LABELS = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_ADMIN: "Admin",
    ROLE_USER: "Élève",
}
ROLE_LABELS_LONG = {
    ROLE_SUPER_ADMIN: "Super Administrateur",
    ROLE_ADMIN: "Administrateur",
    ROLE_USER: "Élève",
}

# ---------------------------------------------------------------------------
# Informations de classe (dossier scolaire de l'élève)
# ---------------------------------------------------------------------------
GENDERS = {"garcon": "Garçon", "fille": "Fille"}
#: Groupes proposés par défaut (le super administrateur peut en créer d'autres : 4, 5…)
GROUPS = (1, 2, 3)
DEFAULT_LEVELS = (
    "6ème", "5ème", "4ème", "3ème", "2nde", "1ère", "Terminale",
    "Licence 1", "Licence 2", "Licence 3", "Master 1", "Master 2",
)

STATUS_ACTIVE = "active"
STATUS_SUSPENDED = "suspended"
STATUS_DISABLED = "disabled"


def utcnow() -> datetime:
    """Date UTC naïve (compatible SQLite et PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(190), unique=True, nullable=True, index=True)
    full_name = db.Column(db.String(160), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_USER, index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE, index=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    bio = db.Column(db.Text, nullable=False, default="")
    avatar_color = db.Column(db.String(16), nullable=False, default="#22d3ee")

    # ---- dossier scolaire (renseigné à l'inscription de l'élève) ----
    last_name = db.Column(db.String(80), default="")
    first_name = db.Column(db.String(80), default="")
    pseudo = db.Column(db.String(64), default="")
    class_number = db.Column(db.Integer)          # numéro dans la liste de classe
    study_level = db.Column(db.String(60), default="")
    gender = db.Column(db.String(12), default="")  # garcon / fille
    class_group = db.Column(db.Integer)            # numéro de groupe choisi par le super admin (1, 2, 3, 4…)
    avatar_filename = db.Column(db.String(255), default="")  # photo de profil envoyée

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)
    password_changed_at = db.Column(db.DateTime, default=utcnow)

    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)

    # relations
    auth_sessions = db.relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    progress = db.relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    attempts = db.relationship("Attempt", back_populates="user", cascade="all, delete-orphan",
                               foreign_keys="Attempt.user_id")

    # ---- helpers -------------------------------------------------------
    @property
    def is_super_admin(self) -> bool:
        return self.role == ROLE_SUPER_ADMIN

    @property
    def is_admin(self) -> bool:
        return self.role in (ROLE_SUPER_ADMIN, ROLE_ADMIN)

    @property
    def is_active_account(self) -> bool:
        return self.status == STATUS_ACTIVE

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)

    # ---- dossier scolaire ------------------------------------------------
    @property
    def gender_label(self) -> str:
        return GENDERS.get(self.gender or "", "")

    @property
    def group_label(self) -> str:
        return f"Groupe {self.class_group}" if self.class_group else ""

    @property
    def display_name(self) -> str:
        """Nom à afficher : nom complet, sinon pseudo, sinon identifiant."""
        return (self.full_name or self.pseudo or self.username or "?").strip()

    @property
    def class_label(self) -> str:
        """Résumé lisible du dossier : niveau · groupe · n°."""
        parts = [part for part in (self.study_level, self.group_label,
                                   f"N° {self.class_number}" if self.class_number else "")
                 if part]
        return " · ".join(parts)

    @property
    def has_avatar(self) -> bool:
        return bool((self.avatar_filename or "").strip())

    @property
    def has_class_record(self) -> bool:
        return any((self.last_name, self.first_name, self.pseudo, self.class_number,
                    self.study_level, self.gender, self.class_group))

    @property
    def initials(self) -> str:
        base = (self.full_name or self.username or "?").strip()
        parts = [p for p in base.replace("-", " ").replace("_", " ").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def set_password(self, raw: str) -> None:
        self.password_hash = hash_password(raw)
        self.password_changed_at = utcnow()

    def check_password(self, raw: str) -> bool:
        ok, rehash_needed = verify_password(self.password_hash, raw)
        if ok and rehash_needed:
            self.password_hash = hash_password(raw)
        return ok

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > utcnow())

    def is_online(self, window_seconds: int = 120) -> bool:
        if not self.last_seen_at:
            return False
        return self.last_seen_at >= utcnow() - timedelta(seconds=window_seconds)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "role_label": self.role_label,
            "initials": self.initials,
            "color": self.avatar_color,
            "online": self.is_online(),
        }


class AuthSession(db.Model):
    """Session serveur révocable (jeton haché stocké en base)."""
    __tablename__ = "auth_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    ip = db.Column(db.String(64), default="")
    user_agent = db.Column(db.String(255), default="")

    user = db.relationship("User", back_populates="auth_sessions")

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > utcnow()


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_label = db.Column(db.String(120), nullable=False, default="système")
    action = db.Column(db.String(80), nullable=False, index=True)
    target = db.Column(db.String(190), default="")
    details = db.Column(db.Text, default="")
    ip = db.Column(db.String(64), default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])


class PasswordResetRequest(db.Model):
    __tablename__ = "password_reset_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending / approved / used / rejected
    token_hash = db.Column(db.String(64), unique=True)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    handled_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    note = db.Column(db.String(255), default="")

    user = db.relationship("User", foreign_keys=[user_id])


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default="")
    icon = db.Column(db.String(40), default="chip")
    order_index = db.Column(db.Integer, default=0)

    modules = db.relationship("Module", back_populates="category")


class Module(db.Model):
    __tablename__ = "modules"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(190), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    summary = db.Column(db.Text, default="")
    description = db.Column(db.Text, default="")
    image_url = db.Column(db.String(400), default="")
    icon = db.Column(db.String(40), default="book-open")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    level = db.Column(db.String(20), default="débutant")
    order_index = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="published", index=True)  # draft / published / archived
    estimated_minutes = db.Column(db.Integer, default=60)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category", back_populates="modules")
    lessons = db.relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                              order_by="Lesson.order_index")
    resources = db.relationship("Resource", back_populates="module", cascade="all, delete-orphan")
    exercises = db.relationship("Exercise", back_populates="module", cascade="all, delete-orphan")

    @property
    def published_lessons(self):
        return [l for l in self.lessons if l.published]


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(190), nullable=False)
    content = db.Column(db.Text, default="")          # contenu pédagogique (texte structuré)
    image_url = db.Column(db.String(400), default="")
    video_url = db.Column(db.String(400), default="")
    document_url = db.Column(db.String(400), default="")
    order_index = db.Column(db.Integer, default=0)
    estimated_minutes = db.Column(db.Integer, default=10)
    published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    module = db.relationship("Module", back_populates="lessons")


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(190), nullable=False)
    url = db.Column(db.String(400), default="")
    filename = db.Column(db.String(255), default="")
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)

    module = db.relationship("Module", back_populates="resources")


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"
    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User", back_populates="progress")
    lesson = db.relationship("Lesson")


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    title = db.Column(db.String(190), nullable=False)
    description = db.Column(db.Text, default="")
    kind = db.Column(db.String(20), default="exercise", index=True)  # exercise / exam
    term = db.Column(db.String(30), default="")                      # T1 / T2 / T3
    duration_minutes = db.Column(db.Integer, default=20)
    pass_score = db.Column(db.Integer, default=50)                   # pourcentage
    max_tab_violations = db.Column(db.Integer, default=1)
    published = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=utcnow)

    module = db.relationship("Module", back_populates="exercises")
    questions = db.relationship("Question", back_populates="exercise", cascade="all, delete-orphan",
                                order_by="Question.order_index")
    attempts = db.relationship("Attempt", back_populates="exercise", cascade="all, delete-orphan")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, default="")
    points = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, default=0)

    exercise = db.relationship("Exercise", back_populates="questions")
    options = db.relationship("Option", back_populates="question", cascade="all, delete-orphan",
                              order_by="Option.order_index")

    @property
    def correct_option(self):
        for o in self.options:
            if o.is_correct:
                return o
        return None


class Option(db.Model):
    __tablename__ = "options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text = db.Column(db.String(400), nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=0)

    question = db.relationship("Question", back_populates="options")


class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    submitted_at = db.Column(db.DateTime)
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="in_progress", index=True)  # in_progress / submitted / eliminated
    tab_violations = db.Column(db.Integer, default=0)
    elimination_reason = db.Column(db.String(255), default="")
    last_heartbeat = db.Column(db.DateTime)
    reset_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reset_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="attempts", foreign_keys=[user_id])
    exercise = db.relationship("Exercise", back_populates="attempts")
    answers = db.relationship("Answer", back_populates="attempt", cascade="all, delete-orphan")

    @property
    def percentage(self) -> int:
        if not self.max_score:
            return 0
        return round(self.score * 100 / self.max_score)

    @property
    def passed(self) -> bool:
        return self.percentage >= (self.exercise.pass_score if self.exercise else 50)


class Answer(db.Model):
    __tablename__ = "answers"
    __table_args__ = (db.UniqueConstraint("attempt_id", "question_id", name="uq_answer_attempt_question"),)

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey("options.id", ondelete="CASCADE"))
    is_correct = db.Column(db.Boolean, default=False)
    points_awarded = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=utcnow)

    attempt = db.relationship("Attempt", back_populates="answers")
    question = db.relationship("Question")
    option = db.relationship("Option")


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(190), nullable=False)
    body = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    author = db.relationship("User")


class MessageRead(db.Model):
    """Accusé de lecture d'un message (une ligne par lecteur)."""
    __tablename__ = "message_reads"
    __table_args__ = (db.UniqueConstraint("message_id", "user_id", name="uq_message_read"),)

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=utcnow)

    message = db.relationship("Message", backref=db.backref("reads", cascade="all, delete-orphan"))
    user = db.relationship("User")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room = db.Column(db.String(60), nullable=False, index=True)   # general / dm:<min>:<max>
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    deleted = db.Column(db.Boolean, default=False, nullable=False)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])


class BattleRoom(db.Model):
    __tablename__ = "battle_rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    mode = db.Column(db.String(20), nullable=False, default="solo")  # solo / group
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # pending (demande à valider par l'administration) / lobby / running / finished / refused
    status = db.Column(db.String(20), default="pending", index=True)
    current_index = db.Column(db.Integer, default=0)
    question_count = db.Column(db.Integer, default=5)
    question_ids = db.Column(db.Text, default="")       # ids séparés par des virgules
    question_started_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)
    finished_at = db.Column(db.DateTime)

    owner = db.relationship("User")
    members = db.relationship("BattleMember", back_populates="room", cascade="all, delete-orphan")

    def qids(self):
        return [int(x) for x in (self.question_ids or "").split(",") if x.strip().isdigit()]


class BattleMember(db.Model):
    __tablename__ = "battle_members"
    __table_args__ = (db.UniqueConstraint("room_id", "user_id", name="uq_battle_member"),)

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("battle_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Integer, default=0)
    answered_index = db.Column(db.Integer, default=-1)
    last_answer_correct = db.Column(db.Boolean)
    joined_at = db.Column(db.DateTime, default=utcnow)

    room = db.relationship("BattleRoom", back_populates="members")
    user = db.relationship("User")


class Notification(db.Model):
    """Notification destinée à un utilisateur (message, battle, annonce, note…).

    Le champ `read_at` vide signifie « non lue ». Les notifications sont
    supprimées en cascade avec le compte : aucune trace personnelle ne survit
    à une suppression RGPD.
    """
    __tablename__ = "notifications"
    __table_args__ = (
        db.Index("ix_notifications_user_read", "user_id", "read_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False, default="system", index=True)
    title = db.Column(db.String(190), nullable=False)
    body = db.Column(db.String(400), default="")
    url = db.Column(db.String(255), default="")
    icon = db.Column(db.String(30), default="bell")
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    read_at = db.Column(db.DateTime, index=True)

    user = db.relationship("User", foreign_keys=[user_id])
    actor = db.relationship("User", foreign_keys=[actor_id])

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, default="")

    @staticmethod
    def get(key: str, default: str = "") -> str:
        row = db.session.get(Setting, key)
        return row.value if row else default

    @staticmethod
    def set(key: str, value: str) -> None:
        row = db.session.get(Setting, key)
        if row:
            row.value = value
        else:
            db.session.add(Setting(key=key, value=value))


# ---------------------------------------------------------------------------
# Fil d'actualité du profil (publications, réactions, commentaires)
# ---------------------------------------------------------------------------
#: Réactions disponibles, dans l'ordre d'affichage.
REACTION_KINDS = {
    "love": "\u2764\ufe0f",   # cœur
    "haha": "\U0001F602",      # rire aux larmes
    "fist": "\U0001F44A",      # coup de poing
    "angry": "\U0001F620",     # colère
    "sad": "\U0001F622",       # triste
}
REACTION_LABELS = {
    "love": "J'aime",
    "haha": "Rire",
    "fist": "Bravo",
    "angry": "Colère",
    "sad": "Triste",
}


class Post(db.Model):
    """Publication du fil d'actualité (texte, photo, ou les deux)."""

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    body = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), default="")
    image_name = db.Column(db.String(255), default="")
    image_size = db.Column(db.Integer, default=0)
    deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    author = db.relationship("User")
    reactions = db.relationship("PostReaction", back_populates="post",
                                cascade="all, delete-orphan")
    comments = db.relationship("PostComment", back_populates="post",
                               cascade="all, delete-orphan", order_by="PostComment.created_at")

    # ---- helpers -------------------------------------------------------
    def reaction_summary(self) -> list[dict]:
        """Réactions agrégées, dans l'ordre officiel des emojis."""
        counts = {}
        for reaction in self.reactions:
            counts[reaction.kind] = counts.get(reaction.kind, 0) + 1
        return [
            {"kind": kind, "emoji": REACTION_KINDS[kind], "label": REACTION_LABELS[kind],
             "count": counts.get(kind, 0)}
            for kind in REACTION_KINDS if counts.get(kind)
        ]

    def my_reaction(self, user_id: int) -> str:
        for reaction in self.reactions:
            if reaction.user_id == user_id:
                return reaction.kind
        return ""

    def reaction_count(self) -> int:
        return len(self.reactions)


class PostReaction(db.Model):
    """Une seule réaction par personne et par publication (modifiable)."""

    __tablename__ = "post_reactions"
    __table_args__ = (db.UniqueConstraint("post_id", "user_id", name="uq_reaction_post_user"),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    kind = db.Column(db.String(12), nullable=False, default="love")
    created_at = db.Column(db.DateTime, default=utcnow)

    post = db.relationship("Post", back_populates="reactions")
    user = db.relationship("User")


class PostComment(db.Model):
    __tablename__ = "post_comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    post = db.relationship("Post", back_populates="comments")
    author = db.relationship("User")
