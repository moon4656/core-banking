from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Role, require_admin, require_readonly
from app.models.knowledge_model import ApiCatalog
from app.schemas.tool import (
    ToolCreateRequest,
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolResponse,
    ToolUpdateRequest,
)
from app.tools.tool_gateway import get_all_tools, invoke_tool

router = APIRouter(prefix="/api/v1/tools", tags=["tool"])


@router.get("", response_model=list[ToolResponse])
def list_tools(
    db: Session = Depends(get_db),
    _role: Role = Depends(require_readonly),
):
    return get_all_tools(db)


@router.get("/catalog", response_model=list[ToolResponse])
def list_tool_catalog(
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    return db.query(ApiCatalog).order_by(ApiCatalog.id.asc()).all()


@router.post("/catalog", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
def create_tool_catalog(
    body: ToolCreateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    existing = db.query(ApiCatalog).filter(ApiCatalog.api_id == body.api_id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="api already exists")

    tool = ApiCatalog(
        api_id=body.api_id,
        name=body.name,
        endpoint=body.endpoint,
        method=body.method,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


@router.put("/catalog/{api_id}", response_model=ToolResponse)
def update_tool_catalog(
    api_id: str,
    body: ToolUpdateRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    tool = db.query(ApiCatalog).filter(ApiCatalog.api_id == api_id).first()
    if tool is None:
        raise HTTPException(status_code=404, detail="api not found")

    tool.name = body.name
    tool.endpoint = body.endpoint
    tool.method = body.method
    tool.description = body.description
    tool.is_active = body.is_active
    db.commit()
    db.refresh(tool)
    return tool


@router.delete("/catalog/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool_catalog(
    api_id: str,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    tool = db.query(ApiCatalog).filter(ApiCatalog.api_id == api_id).first()
    if tool is None:
        raise HTTPException(status_code=404, detail="api not found")
    db.delete(tool)
    db.commit()


@router.post("/invoke", response_model=ToolInvokeResponse)
async def invoke(
    body: ToolInvokeRequest,
    db: Session = Depends(get_db),
    _role: Role = Depends(require_admin),
):
    return await invoke_tool(db, body.api_id, body.params)
