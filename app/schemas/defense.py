from pydantic import BaseModel


class RiskSummary(BaseModel):
    user_id: str
    login_risk: float
    network_risk: float
    temporal_risk: float
    mutation_risk: float
    aggregate_risk: float
    recommended_action: str
