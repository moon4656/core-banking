from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, alias="apiKey")


class SessionResponse(BaseModel):
    name: str
    role: str
    auth_mode: str
    access_token: str
    token_type: str = "bearer"
