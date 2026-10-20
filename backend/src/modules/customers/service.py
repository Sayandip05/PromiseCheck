"""Customer domain service for account management and SLA health aggregation."""

import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.commitments import CommitmentService
from modules.customers.models import Customer


class CustomerService:
    """Encapsulates customer account operations and dynamic SLA health metrics."""

    @staticmethod
    async def list_customers_with_metrics(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List customer accounts with dynamically computed commitment health scores."""
        count_res = await db.execute(
            select(func.count(Customer.id)).where(Customer.workspace_id == workspace_id)
        )
        total = count_res.scalar_one()

        res = await db.execute(
            select(Customer)
            .where(Customer.workspace_id == workspace_id)
            .order_by(Customer.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        customers = res.scalars().all()

        commitments = await CommitmentService.list_all_workspace_commitments(db, workspace_id)

        dto_list: list[dict[str, Any]] = []
        for c in customers:
            c_name_clean = c.name.lower().strip()
            matching = [
                comm
                for comm in commitments
                if comm.customer_name.lower().strip() in c_name_clean
                or c_name_clean in comm.customer_name.lower().strip()
            ]

            if matching:
                active_count = sum(1 for comm in matching if comm.status != "delivered")
                at_risk_count = sum(1 for comm in matching if comm.status == "at-risk")
                if at_risk_count > 0:
                    c_status = "at-risk"
                    c_color = "#f59e0b"
                    health = max(50, 90 - (at_risk_count * 20))
                elif active_count > 0:
                    c_status = "on-track"
                    c_color = "#10b981"
                    health = 95
                else:
                    c_status = "completed"
                    c_color = "#10b981"
                    health = 100

                recent = matching[-1].title
                due = matching[-1].promised_by or c.due_date
            else:
                c_status = c.status
                c_color = c.status_color
                active_count = c.active_promises
                health = c.health_score
                recent = c.recent_promise
                due = c.due_date

            dto_list.append({
                "id": str(c.id),
                "name": c.name,
                "status": c_status,
                "statusColor": c_color,
                "activePromises": active_count,
                "healthScore": health,
                "recentPromise": recent,
                "dueDate": due,
                "owner": c.owner,
            })

        return dto_list, total

    @staticmethod
    async def create_customer(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        name: str,
        owner: Optional[str] = "Account Manager",
        recent_promise: Optional[str] = "",
        due_date: Optional[str] = "",
    ) -> Customer:
        """Create a new customer account in the active workspace."""
        customer = Customer(
            workspace_id=workspace_id,
            name=name,
            owner=owner or "Account Manager",
            recent_promise=recent_promise or "Initial onboarding",
            due_date=due_date or "Upcoming",
            status="on-track",
            status_color="#10b981",
            active_promises=1,
            health_score=100,
            domains_json=[],
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_customer_by_id(
        db: AsyncSession,
        customer_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Customer:
        """Fetch customer ensuring tenant isolation."""
        customer = await db.get(Customer, customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        if customer.workspace_id != workspace_id:
            # Return 404 rather than 403 so we never leak the existence of a
            # customer record belonging to another tenant.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer
