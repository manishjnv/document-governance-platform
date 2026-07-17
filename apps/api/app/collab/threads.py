"""Pure function to build comment tree from flat list."""

from typing import Any


def build_comment_tree(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Nest comment replies under their parents.

    Args:
        comments: flat list of comment dicts, each with 'comment_id' and 'parent_comment_id'

    Returns:
        List of top-level comments (parent_comment_id is None) with nested 'children' key
        containing their replies (recursively nested). Pure function — does not mutate input.
    """
    # Build a map of comment_id -> comment dict (with empty children list)
    comment_map: dict[str, dict[str, Any]] = {}
    for comment in comments:
        comment_copy = dict(comment)  # shallow copy to avoid mutating input
        comment_copy["children"] = []
        comment_map[str(comment_copy.get("comment_id", ""))] = comment_copy

    # Build the tree
    top_level = []
    for comment in comments:
        parent_id = comment.get("parent_comment_id")
        comment_id = str(comment.get("comment_id", ""))

        if parent_id is None or parent_id == "":
            # Top-level comment
            top_level.append(comment_map[comment_id])
        else:
            # Reply: attach to parent
            parent_key = str(parent_id)
            if parent_key in comment_map:
                comment_map[parent_key]["children"].append(comment_map[comment_id])

    return top_level
