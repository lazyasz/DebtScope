"""First Google login gives the user their own empty workspace, once."""
from backend.database.models import User, Workspace, WorkspaceMembership
from backend.services.auth_service import _ensure_personal_workspace


def test_personal_workspace_created_once(db_session):
    user = User(id="usr_google_1", email="ada@example.com", full_name="Ada Lovelace", is_active=True)
    db_session.add(user)
    db_session.commit()

    _ensure_personal_workspace(db_session, user)
    _ensure_personal_workspace(db_session, user)

    memberships = db_session.query(WorkspaceMembership).filter_by(user_id=user.id).all()
    assert len(memberships) == 1
    ws = db_session.get(Workspace, memberships[0].workspace_id)
    assert ws.owner_id == user.id
    assert not ws.is_demo
    assert ws.name == "Ada's Workspace"
