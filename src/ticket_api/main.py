"""Minimal helpdesk ticketing API.

This is the external system that the Copilot Studio agent reaches through a
Power Automate flow and a custom connector (see connectors/helpdesk-ticketing).

Design choices that matter for a reliable automation:
- API-key auth (in Azure the key lives in Key Vault, never in the flow).
- Idempotency-Key header, so a Power Automate retry never creates a duplicate ticket.
- Strict input validation, so bad data fails fast with a clear 422 instead of
  creating a half-filled ticket.
- High-risk requests are created in "PendingApproval" status unless the caller
  passes an approval reference, so the human-approval rule is enforced server-side too.
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

API_KEY_ENV = "HELPDESK_API_KEY"

app = FastAPI(
    title="Helpdesk Ticketing API",
    version="1.0.0",
    description="Ticketing backend for the M365 AI IT Helpdesk Agent sample.",
)


class Category(str, Enum):
    account = "Account"
    email = "Email"
    device = "Device"
    network = "Network"
    software = "Software"
    security = "Security"
    other = "Other"


class Priority(str, Enum):
    low = "Low"
    normal = "Normal"
    high = "High"
    urgent = "Urgent"


class TicketStatus(str, Enum):
    pending_approval = "PendingApproval"
    open = "Open"
    in_progress = "InProgress"
    resolved = "Resolved"
    rejected = "Rejected"


# Requests that change access or security settings need a human approval first.
HIGH_RISK_CATEGORIES = {Category.account, Category.security}
HIGH_RISK_KEYWORDS = ("mailbox access", "admin rights", "disable mfa", "password reset", "delete")


class TicketCreate(BaseModel):
    requester_upn: str = Field(..., description="User principal name of the requester", examples=["abebe@contoso.org"])
    title: str = Field(..., min_length=5, max_length=120)
    description: str = Field(..., min_length=10, max_length=4000)
    category: Category
    priority: Priority = Priority.normal
    source: str = Field("CopilotAgent", max_length=40)
    approval_id: str | None = Field(None, description="Approval reference when a manager has already approved")

    @field_validator("requester_upn")
    @classmethod
    def upn_must_look_like_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("requester_upn must be a user principal name such as name@domain")
        return v


class Ticket(TicketCreate):
    id: str
    status: TicketStatus
    requires_approval: bool
    created_utc: datetime
    updated_utc: datetime


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    approval_id: str | None = None
    note: str | None = Field(None, max_length=2000)


class _Store:
    """Thread-safe in-memory store. Swap for Dataverse or SQL in production."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.tickets: dict[str, Ticket] = {}
        self.idempotency: dict[str, str] = {}

    def reset(self) -> None:
        with self._lock:
            self.tickets.clear()
            self.idempotency.clear()


store = _Store()


def require_api_key(x_api_key: str | None = Header(None)) -> None:
    expected = os.environ.get(API_KEY_ENV)
    if not expected:
        raise HTTPException(status_code=500, detail=f"{API_KEY_ENV} is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


def is_high_risk(payload: TicketCreate) -> bool:
    text = f"{payload.title} {payload.description}".lower()
    return payload.category in HIGH_RISK_CATEGORIES or any(k in text for k in HIGH_RISK_KEYWORDS)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "tickets": len(store.tickets)}


@app.post("/tickets", response_model=Ticket, status_code=201, tags=["tickets"], operation_id="CreateTicket",
          dependencies=[Depends(require_api_key)])
def create_ticket(payload: TicketCreate, idempotency_key: str | None = Header(None)) -> Ticket:
    with store._lock:
        if idempotency_key and idempotency_key in store.idempotency:
            return store.tickets[store.idempotency[idempotency_key]]
        risky = is_high_risk(payload)
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            **payload.model_dump(),
            id=f"HD-{uuid.uuid4().hex[:8].upper()}",
            status=TicketStatus.pending_approval if risky and not payload.approval_id else TicketStatus.open,
            requires_approval=risky,
            created_utc=now,
            updated_utc=now,
        )
        store.tickets[ticket.id] = ticket
        if idempotency_key:
            store.idempotency[idempotency_key] = ticket.id
        return ticket


@app.get("/tickets/{ticket_id}", response_model=Ticket, tags=["tickets"], operation_id="GetTicket",
         dependencies=[Depends(require_api_key)])
def get_ticket(ticket_id: str) -> Ticket:
    ticket = store.tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/tickets/{ticket_id}", response_model=Ticket, tags=["tickets"], operation_id="UpdateTicket",
           dependencies=[Depends(require_api_key)])
def update_ticket(ticket_id: str, update: TicketUpdate) -> Ticket:
    with store._lock:
        ticket = store.tickets.get(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        # A high-risk ticket cannot be opened without an approval reference.
        if (ticket.requires_approval and update.status in (TicketStatus.open, TicketStatus.in_progress)
                and not (update.approval_id or ticket.approval_id)):
            raise HTTPException(status_code=409, detail="High-risk ticket needs an approval_id before it can be opened")
        data = ticket.model_dump()
        for field in ("status", "approval_id"):
            value = getattr(update, field)
            if value is not None:
                data[field] = value
        if update.note:
            data["description"] = f"{ticket.description}\n\n[{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC] {update.note}"
        data["updated_utc"] = datetime.now(timezone.utc)
        updated = Ticket(**data)
        store.tickets[ticket_id] = updated
        return updated
