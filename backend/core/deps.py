from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Annotated
from uuid import UUID
from .database import get_db
from .security import verify_access_token
from .config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the current user from JWT."""
    from models.user import User  # avoid circular import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    user_id = verify_access_token(credentials.credentials)
    if not user_id:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or suspended",
        )

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    return current_user


def require_permission(module: str, action: str):
    """Permission-based dependency factory."""
    async def _check(current_user=Depends(get_current_user)):
        from models.user import Role
        perms = current_user.role.permissions if current_user.role else {}

        # Super admin has all permissions
        if perms.get("all"):
            return current_user

        allowed_actions = perms.get(module, [])
        if action not in allowed_actions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {module}.{action}",
            )
        return current_user
    return _check


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=500, description="Items per page"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


def get_company_id(current_user=Depends(get_current_user)) -> UUID:
    return current_user.company_id


# Type aliases for cleaner route signatures
CurrentUser = Annotated[object, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
Pages = Annotated[Pagination, Depends()]
CompanyID = Annotated[UUID, Depends(get_company_id)]
