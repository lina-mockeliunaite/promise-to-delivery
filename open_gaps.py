"""The one place that says which gaps are open (21 Oct).

A gap is open for the screens when the ledger says it is not Resolved, or when it is Resolved but the signed paperwork lacks the fix
(signed_check.py: "Needs attention" again). Every count of open gaps, on the deal list, the stage bar, the deal page's numbers, the
decision summary and the "is there an open contract gap" reading, goes through `rows` here, so no count can leave the signed-contract
overlay out. tests/test_open_gaps_single_source.py fails if SQL elsewhere computes "not Resolved" itself, or if a new module reads
issue_current_state without being listed there.

The ledger itself is not changed: this is a read-time view.
"""

OPEN_SQL = (
    "SELECT i.id, i.commitment_id, i.issue_type, i.subject_key, i.closure_criteria FROM issues i"
    " JOIN issue_current_state s ON s.issue_id = i.id JOIN commitments c ON c.id = i.commitment_id"
    " WHERE c.deal_id = ? AND s.state <> 'Resolved' ORDER BY i.id")


def effective_state(state, check):
    """The state a screen shows for one gap: "Needs action" when the signed check found the fix missing, else the ledger's state."""
    return "Needs action" if check and check.get("status") == "not_found" else state


def rows(conn, did: int, slug: str = None) -> list:
    """[(issue id, commitment id, issue type, subject key, closure criteria)] for every gap that counts as open, in issue order."""
    if slug is None:
        import deal_catalogue
        slug = deal_catalogue.slug_of(conn, did)
    found = conn.execute(OPEN_SQL, (did,)).fetchall()
    if slug:
        import signed_check
        back = signed_check.reopened(conn, did, slug)
        if back:
            found += conn.execute(
                "SELECT id, commitment_id, issue_type, subject_key, closure_criteria FROM issues"
                f" WHERE id IN ({','.join('?' * len(back))})", tuple(back)).fetchall()
    return sorted(found, key=lambda r: r[0])


def issue_ids(conn, did: int, slug: str = None) -> set:
    return {r[0] for r in rows(conn, did, slug)}


def commitment_ids(conn, did: int, slug: str = None) -> set:
    return {r[1] for r in rows(conn, did, slug)}


def count(conn, did: int, slug: str = None) -> int:
    return len(rows(conn, did, slug))
