"""
AI Copilot API Routes.
Provides streaming SSE chat endpoint, tenant-scoped tool calling,
and conversation persistence.
"""

import uuid
import json
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.tenant import get_current_user, get_current_workspace
from backend.database.models import User, Workspace, CopilotConversation, CopilotMessage, SourceFile, PendingAction
from backend.services.copilot_tools import CopilotToolRegistry
from backend.services.copilot_llm import get_copilot_llm, CopilotStreamEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["AI Copilot & AST Refactoring"])


class ChatMessagePayload(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    repository_id: Optional[int] = None
    stream: bool = True
    user_confirmation: bool = False


class ConversationSummary(BaseModel):
    id: str
    workspace_id: str
    title: str
    repository_id: Optional[int]
    created_at: str
    updated_at: str
    message_count: int


@router.post("/chat", summary="Interactive Grounded Copilot Chat (SSE Streaming)")
async def chat_copilot(
    payload: ChatMessagePayload,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
    workspace: Optional[Workspace] = Depends(get_current_workspace),
):
    """
    Primary Copilot Chat endpoint with Server-Sent Events (SSE) streaming.
    Workspace ID and Repository ID are enforced from user session, ensuring tenant isolation.
    """
    workspace_id = workspace.id if workspace else "ws_demo"
    user_id = user.id if user else "usr_lead_01"
    repo_id = payload.repository_id

    # If repo_id not passed, pick first active repository in workspace
    if not repo_id:
        first_file = db.query(SourceFile).filter(SourceFile.workspace_id == workspace_id).first()
        repo_id = first_file.repository_id if first_file else 1

    # 1. Resolve or Create Conversation
    conv = None
    if payload.conversation_id:
        conv = db.query(CopilotConversation).filter(
            CopilotConversation.id == payload.conversation_id,
            CopilotConversation.workspace_id == workspace_id,
        ).first()

    if not conv:
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        conv = CopilotConversation(
            id=conv_id,
            workspace_id=workspace_id,
            user_id=user_id,
            repository_id=repo_id,
            title=payload.message[:60] if payload.message else "Copilot Session",
        )
        db.add(conv)
        db.commit()
    else:
        conv_id = conv.id

    # 2. Persist User Message
    user_msg = CopilotMessage(
        conversation_id=conv_id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    # 3. Build Conversation History Context
    prev_messages = db.query(CopilotMessage).filter(
        CopilotMessage.conversation_id == conv_id
    ).order_by(CopilotMessage.created_at.asc()).all()

    history = [{"role": m.role, "content": m.content} for m in prev_messages]

    # 4. Initialize Tenant-Scoped Tool Registry
    tool_registry = CopilotToolRegistry(db=db, workspace_id=workspace_id, repository_id=repo_id, user_id=user_id)
    llm = get_copilot_llm()

    async def event_generator():
        yield f"data: {json.dumps({'type': 'init', 'data': {'conversation_id': conv_id}})}\n\n"

        assistant_tokens = []
        citations = []
        tool_calls = []
        refactor_diff = None

        try:
            async for ev in llm.stream_chat(history, tool_registry):
                if ev.event_type == "token":
                    assistant_tokens.append(ev.data)
                elif ev.event_type == "citation":
                    citations.append(ev.data)
                elif ev.event_type == "tool_call":
                    tool_calls.append(ev.data)
                elif ev.event_type == "refactor_diff":
                    refactor_diff = ev.data

                yield ev.to_sse()

            # Save assistant message
            full_reply = "".join(assistant_tokens)
            asst_msg = CopilotMessage(
                conversation_id=conv_id,
                role="assistant",
                content=full_reply,
                citations_json=json.dumps(citations) if citations else None,
                tool_calls_json=json.dumps(tool_calls) if tool_calls else None,
                refactor_diff=json.dumps(refactor_diff) if refactor_diff else None,
            )
            db.add(asst_msg)
            db.commit()

        except Exception as e:
            logger.exception("Error during Copilot stream: %s", e)
            err_ev = CopilotStreamEvent("error", f"Copilot execution failure: {str(e)}")
            yield err_ev.to_sse()

    if payload.stream:
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response for synchronous legacy clients
    reply_tokens = []
    cits = []
    t_calls = []
    r_diff = None

    async for ev in llm.stream_chat(history, tool_registry):
        if ev.event_type == "token":
            reply_tokens.append(ev.data)
        elif ev.event_type == "citation":
            cits.append(ev.data)
        elif ev.event_type == "tool_call":
            t_calls.append(ev.data)
        elif ev.event_type == "refactor_diff":
            r_diff = ev.data

    full_text = "".join(reply_tokens)
    asst_msg = CopilotMessage(
        conversation_id=conv_id,
        role="assistant",
        content=full_text,
        citations_json=json.dumps(cits) if cits else None,
        tool_calls_json=json.dumps(t_calls) if t_calls else None,
        refactor_diff=json.dumps(r_diff) if r_diff else None,
    )
    db.add(asst_msg)
    db.commit()

    return {
        "status": "success",
        "conversation_id": conv_id,
        "reply": full_text,
        "citations": cits,
        "tool_calls": t_calls,
        "refactor_diff": r_diff,
        "suggested_actions": ["Inspect Hotspots", "Explain Score", "Propose Refactor"],
    }


@router.get("/conversations", summary="List Workspace Copilot Conversations")
def list_conversations(
    db: Session = Depends(get_db),
    workspace: Optional[Workspace] = Depends(get_current_workspace),
):
    workspace_id = workspace.id if workspace else "ws_demo"
    convs = db.query(CopilotConversation).filter(
        CopilotConversation.workspace_id == workspace_id
    ).order_by(CopilotConversation.updated_at.desc()).all()

    return [
        {
            "id": c.id,
            "workspace_id": c.workspace_id,
            "title": c.title,
            "repository_id": c.repository_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": len(c.messages),
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", summary="Get Conversation Message History")
def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    workspace: Optional[Workspace] = Depends(get_current_workspace),
):
    workspace_id = workspace.id if workspace else "ws_demo"
    conv = db.query(CopilotConversation).filter(
        CopilotConversation.id == conversation_id,
        CopilotConversation.workspace_id == workspace_id,
    ).first()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found in current workspace.",
        )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": json.loads(m.citations_json) if m.citations_json else [],
            "tool_calls": json.loads(m.tool_calls_json) if m.tool_calls_json else [],
            "refactor_diff": json.loads(m.refactor_diff) if m.refactor_diff else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in conv.messages
    ]


def _verify_origin(request: Request) -> None:
    """Verifies that requests originate from an allowed origin to prevent cross-site action execution."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return  # Same-origin or non-browser client

    parsed = urlparse(origin)
    origin_clean = f"{parsed.scheme}://{parsed.netloc}"
    # Wildcard '*' is never valid for Origin CSRF validation on write confirmation
    allowed = {o for o in settings.ALLOWED_ORIGINS if o != "*"}
    if settings.FRONTEND_URL:
        parsed_fe = urlparse(settings.FRONTEND_URL)
        allowed.add(f"{parsed_fe.scheme}://{parsed_fe.netloc}")

    if origin_clean not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-Origin write confirmation forbidden from origin: {origin_clean}",
        )


@router.get("/actions/{action_id}", summary="Get Staged Pending Action Details")
def get_pending_action(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Fetches the server-stored payload of a staged pending action for UI review.
    Enforces user ownership and tenant workspace isolation.
    """
    action = db.query(PendingAction).filter(PendingAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending action not found.")
    if action.workspace_id != workspace.id or action.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied for this action.")

    return {
        "id": action.id,
        "tool_name": action.tool_name,
        "arguments": json.loads(action.arguments_json),
        "status": action.status,
        "expires_at": action.expires_at.isoformat() if action.expires_at else None,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


@router.post("/actions/{action_id}/confirm", summary="Confirm and Execute Staged Copilot Write Action")
def confirm_action(
    action_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Dedicated user-authenticated endpoint to execute a staged single-use write action.
    Accepts NO client-supplied arguments: strictly executes using the stored payload from the
    server PendingAction record. Origin check protects against CSRF.
    """
    _verify_origin(request)
    return CopilotToolRegistry.execute_confirmed_action(
        db=db,
        action_id=action_id,
        user_id=user.id,
        workspace_id=workspace.id,
    )


