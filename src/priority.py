"""Deadline-driven priority engine."""
from datetime import date


def assign(n, today=None):
    today = today or date.today()
    dl = n.days_left(today)
    if dl is not None and dl < 0:
        n.priority = "Low"
        if n.verification_status not in ("Cancelled",):
            n.verification_status = "Application Closed"
        return n
    if dl is None:
        n.priority = "Low"
    elif dl <= 3:
        n.priority = "Very High"
    elif dl <= 7:
        n.priority = "High"
    elif dl <= 30:
        n.priority = "Medium"
    else:
        n.priority = "Low"
    return n
