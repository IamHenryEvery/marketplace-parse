from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from marketplace_parse.db.enums import UserRole



class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    role: str
    scheduler_enabled: bool


class SchedulerToggleResponse(BaseModel):
    scheduler_enabled: bool



class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    role: str
    scheduler_enabled: bool
    created_at: datetime


class UpdateUserRoleRequest(BaseModel):
    role: UserRole



class MarketplaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    marketplace_id: int
    slug: str
    display_name: str



class ProductURLOut(BaseModel):
    url_id: int
    url: str
    marketplace: MarketplaceOut


class ProductOut(BaseModel):
    product_id: int
    name: str
    created_at: datetime
    urls: list[ProductURLOut]


class ProductURLCreate(BaseModel):
    url: str = Field(min_length=1)
    marketplace_id: int


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    urls: list[ProductURLCreate] = Field(default_factory=list)


class ProductURLUpdate(BaseModel):
    url_id: int
    url: str | None = None
    marketplace_id: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    urls_update: list[ProductURLUpdate] | None = None
    urls_delete: list[int] | None = None
    urls_add: list[ProductURLCreate] | None = None



class ParseTriggerRequest(BaseModel):
    from_date: date | None = None


class ParseTriggerOut(BaseModel):
    run_ids: list[int]


class LastRunInfo(BaseModel):
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    reviews_collected: int
    error_message: str | None


class ParseRunSummary(BaseModel):
    url_id: int
    url: str
    marketplace: MarketplaceOut
    last_run: LastRunInfo | None


class ProgressOut(BaseModel):
    pending: int
    running: int
    completed: int
    failed: int
    in_flight: int
    total: int
    runs: list[ParseRunSummary]



class AnalysisLatest(BaseModel):
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_sentiment: float
    calculated_at: datetime


class AnalysisItem(BaseModel):
    marketplace: MarketplaceOut
    latest: AnalysisLatest | None



class ParseRunListItem(BaseModel):
    run_id: int
    product_id: int
    product_name: str
    url: str
    marketplace: MarketplaceOut
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    reviews_collected: int
    error_message: str | None


class RunAnalysisOut(BaseModel):
    run_id: int
    product_name: str
    marketplace: MarketplaceOut
    status: str
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_sentiment: float




class FeedReviewItem(BaseModel):
    review_id: int
    review_text: str
    review_date: datetime | None
    sentiment_label: str | None
    sentiment_score: float | None
    created_at: datetime
    marketplace: MarketplaceOut
    product_name: str 
