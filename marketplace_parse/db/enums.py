import enum


class UserRole(str, enum.Enum):
    user = "user"
    analyst = "analyst"
    admin = "admin"


class ParseStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class SentimentLabel(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
