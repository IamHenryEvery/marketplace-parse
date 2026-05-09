from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from marketplace_parse.db.base import Base, TimestampMixin
from marketplace_parse.db.enums import ParseStatus, SentimentLabel, UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        nullable=False,
        server_default=UserRole.user.value,
    )
    scheduler_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RoleChangeAudit(Base):
    __tablename__ = "role_change_audit"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    target_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id"), nullable=False
    )
    changed_by_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id"), nullable=False
    )
    old_role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False), nullable=False
    )
    new_role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Marketplace(Base):
    __tablename__ = "marketplaces"

    marketplace_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship(back_populates="products")
    urls: Mapped[list["ProductURL"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductURL(Base):
    __tablename__ = "product_urls"
    __table_args__ = (
        UniqueConstraint("product_id", "url", name="uq_product_url"),
    )

    url_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    marketplace_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("marketplaces.marketplace_id"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    last_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="urls")
    marketplace: Mapped["Marketplace"] = relationship()


class ParseRun(Base):
    __tablename__ = "parse_runs"

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    url_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_urls.url_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ParseStatus] = mapped_column(
        SAEnum(ParseStatus, name="parse_status"),
        nullable=False,
        server_default=ParseStatus.pending.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviews_collected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    review_from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    url_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_urls.url_id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("parse_runs.run_id"), nullable=True
    )
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[date | None] = mapped_column("date", Date, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(
        SAEnum(SentimentLabel, name="sentiment_label"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_result"
    __table_args__ = (
        Index(
            "idx_analysis_product_marketplace_calculated",
            "product_id",
            "marketplace_id",
            text("calculated_at DESC"),
        ),
    )

    analysis_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    marketplace_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("marketplaces.marketplace_id"), nullable=False
    )
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False)
    neutral_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_sentiment: Mapped[float] = mapped_column(Float, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
