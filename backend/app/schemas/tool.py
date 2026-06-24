from pydantic import BaseModel, ConfigDict, Field


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    api_id: str
    name: str
    endpoint: str
    method: str
    description: str | None
    is_active: bool = True


class ToolCreateRequest(BaseModel):
    api_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1, max_length=500)
    method: str = Field(min_length=1, max_length=10)
    description: str | None = None
    is_active: bool = True


class ToolUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1, max_length=500)
    method: str = Field(min_length=1, max_length=10)
    description: str | None = None
    is_active: bool = True


class ToolInvokeRequest(BaseModel):
    api_id: str
    params: dict = {}


class ToolInvokeResponse(BaseModel):
    api_id: str
    status: str
    data: dict | list | None
    error: str | None
    latency_ms: int | None = None
    output_masked: dict | None = None
