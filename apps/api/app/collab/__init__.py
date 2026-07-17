"""Collaboration module: comments, approvals, threads, reactions, digest."""

from app.collab.approvals import (
    create_approval_request,
    decide_approval,
    list_approvals_for_review,
)
from app.collab.comments import create_comment, delete_comment, list_comments_for_doc
from app.collab.digest import build_daily_digest
from app.collab.reactions import get_reaction_counts, toggle_reaction
from app.collab.teams import (
    accept_invitation,
    add_team_member,
    create_team,
    get_team_activity,
    invite_to_team,
    list_org_teams,
    remove_team_member,
    update_member_role,
    update_team_settings,
)
from app.collab.threads import build_comment_tree

__all__ = [
    "create_comment",
    "list_comments_for_doc",
    "delete_comment",
    "create_approval_request",
    "list_approvals_for_review",
    "decide_approval",
    "build_comment_tree",
    "toggle_reaction",
    "get_reaction_counts",
    "build_daily_digest",
    "create_team",
    "list_org_teams",
    "add_team_member",
    "update_member_role",
    "remove_team_member",
    "invite_to_team",
    "accept_invitation",
    "get_team_activity",
    "update_team_settings",
]
