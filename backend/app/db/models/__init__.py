"""Database models package.

Each model is in its own file for clarity and to avoid circular imports.
All models inherit from app.db.base.Base.

Import models from this package (not from individual files) for convenience:
    from app.db.models import User, Experiment, ValidationReport
"""

from app.db.models.chat_attachment import ChatAttachment
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_thread import ChatThread
from app.db.models.coupon import Coupon
from app.db.models.coupon_redemption import CouponRedemption
from app.db.models.experiment import Experiment
from app.db.models.subreddit_selection_hint import SubredditSelectionHint
from app.db.models.external_api_call import ExternalAPICall
from app.db.models.insight_report import InsightReport
from app.db.models.landing_page import LandingPage
from app.db.models.landing_page_v2 import LandingPageV2Spec
from app.db.models.llm_call import LLMCall
from app.db.models.page_view import PageView
from app.db.models.payment_order import PaymentOrder
from app.db.models.processed_webhook import ProcessedWebhook
from app.db.models.user import User
from app.db.models.validation_report import ValidationReport
from app.db.models.waitlist_signup import WaitlistSignup
from app.db.models.wallet import Wallet
from app.db.models.wallet_transaction import WalletTransaction

__all__ = [
    "ChatAttachment",
    "ChatMessage",
    "ChatThread",
    "Coupon",
    "CouponRedemption",
    "Experiment",
    "GeographySourceHint",
    "SubredditSelectionHint",
    "RefinementIdempotency",
    "ExternalAPICall",
    "InsightReport",
    "LandingPage",
    "LandingPageV2Spec",
    "LLMCall",
    "PageView",
    "PaymentOrder",
    "ProcessedWebhook",
    "User",
    "ValidationReport",
    "WaitlistSignup",
    "Wallet",
    "WalletTransaction",
]
