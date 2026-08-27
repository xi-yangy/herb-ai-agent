"""ORM 模型包。

按 PRD 规划建五张表：users、herbs、recognition_history、favorites、privacy_consents。
"""

from app.db.base import Base
from app.models.favorite import Favorite
from app.models.herb import Herb
from app.models.privacy_consent import PrivacyConsent
from app.models.recognition_history import RecognitionHistory
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Herb",
    "RecognitionHistory",
    "Favorite",
    "PrivacyConsent",
]
