"""SQLAlchemy ORM models.

The Alembic baseline (`0001_baseline`) describes exactly these tables. On a
fresh database run `alembic upgrade head`; on a database that already has the
schema run `alembic stamp head` so the baseline is recorded without re-running
the DDL.
"""

from app.models.drawing import WordDrawing
from app.models.example import WordExample
from app.models.exercise import ExerciseResult, GeneratedExercise
from app.models.expression import ExpressionAttempt, UserDailyUsage
from app.models.mastery import UserVocabMastery
from app.models.quiz import Entry, Quiz, QuizEntry
from app.models.review import ReviewLog
from app.models.user import User, UserSetting

__all__ = [
    "Entry",
    "ExerciseResult",
    "ExpressionAttempt",
    "GeneratedExercise",
    "Quiz",
    "QuizEntry",
    "ReviewLog",
    "User",
    "UserDailyUsage",
    "UserSetting",
    "UserVocabMastery",
    "WordDrawing",
    "WordExample",
]
