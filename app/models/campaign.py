from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CampaignBase(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    campaign_type: str  # 'fundraising', 'donation', 'exchange'
    goal_amount: Optional[float] = None
    goal_item: Optional[int] = None

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    goal_amount: Optional[float] = None
    goal_item: Optional[int] = None
    status: Optional[str] = None  # 'active', 'completed', 'cancelled'

class CampaignInDB(CampaignBase):
    campaign_id: int
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_by: int
    current_amount: float = 0.0
    status: str = "active"
