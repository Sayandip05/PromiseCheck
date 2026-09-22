"""Unit tests for workspace invitation token expiry and DB-level filtering."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from core.database import AsyncSessionLocal
from modules.workspaces.models import Invitation, Workspace
from modules.workspaces.service import WorkspaceService


@pytest.mark.asyncio
async def test_invitation_valid_and_expiry_filtering():
    """Verify get_valid_invitation filters out expired or already accepted tokens at DB level."""
    async with AsyncSessionLocal() as db:
        # Create a workspace for testing invitations
        ws = Workspace(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:6]}")
        db.add(ws)
        await db.flush()

        # 1. Valid invitation (unexpired, unaccepted)
        inv_valid, raw_token_valid = await WorkspaceService.create_invitation(
            db=db,
            workspace_id=ws.id,
            email="valid@example.com",
            expires_delta_hours=48,
        )
        await db.commit()

        found_valid = await WorkspaceService.get_valid_invitation(db, inv_valid.token_hash)
        assert found_valid is not None
        assert found_valid.email == "valid@example.com"
        assert found_valid.id == inv_valid.id

        # 2. Expired invitation (expires_at in the past)
        inv_expired, _ = await WorkspaceService.create_invitation(
            db=db,
            workspace_id=ws.id,
            email="expired@example.com",
            expires_delta_hours=-5,
        )
        await db.commit()

        found_expired = await WorkspaceService.get_valid_invitation(db, inv_expired.token_hash)
        assert found_expired is None, "Expired invitation must be filtered out by DB query"

        # 3. Already accepted invitation
        inv_accepted, _ = await WorkspaceService.create_invitation(
            db=db,
            workspace_id=ws.id,
            email="accepted@example.com",
            expires_delta_hours=24,
        )
        inv_accepted.accepted_at = datetime.now(timezone.utc)
        await db.commit()

        found_accepted = await WorkspaceService.get_valid_invitation(db, inv_accepted.token_hash)
        assert found_accepted is None, "Accepted invitation must be filtered out by DB query"

        # 4. Unknown token hash
        unknown = await WorkspaceService.get_valid_invitation(db, "nonexistenthash123")
        assert unknown is None
