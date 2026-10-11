"""IAM domain module public interface."""

from modules.iam.dependencies import (
    extract_access_token,
    extract_access_token_optional,
    get_current_user,
    get_current_user_optional,
    require_role,
)
from modules.iam.models import User
from modules.iam.service import (
    AuthService,
    IdentityService,
    WorkspaceService,
    get_active_workspace_id,
    get_user_by_id,
)

__all__ = [
    "User",
    "get_current_user",
    "get_current_user_optional",
    "extract_access_token",
    "extract_access_token_optional",
    "require_role",
    "get_active_workspace_id",
    "get_user_by_id",
    "IdentityService",
    "AuthService",
    "WorkspaceService",
]
