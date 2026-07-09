"""Data model for a recruitment/exam notification."""
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
import hashlib
import re

VERIFICATION_STATES = [
    "Verified", "Verified with Official PDF", "Verified with Official Website",
    "Verified with Official Notification", "Unverified", "Expired", "Cancelled",
    "Application Closed", "Result Released", "Admit Card Released",
    "Answer Key Released", "Final Result Released",
]

TRACK_STATES = [
    "Not Applied", "Applied", "Application Submitted", "Fee Pending", "Fee Paid",
    "Exam Scheduled", "Admit Card Available", "Exam Completed", "Answer Key Released",
    "Result Awaited", "Result Declared", "Interview", "Document Verification",
    "Offer Released", "Rejected", "Completed", "Already Applied",
]

PRIORITIES = ["Very High", "High", "Medium", "Low"]

APPLIED_STATES = {
    "Applied", "Application Submitted", "Already Applied", "Fee Pending", "Fee Paid",
    "Exam Scheduled", "Admit Card Available", "Exam Completed", "Result Awaited",
}


def is_applied(status):
    return status in APPLIED_STATES


@dataclass
class Notification:
    notification_id: str = ""
    job_name: str = ""
    exam_name: str = ""
    department: str = ""
    organization: str = ""
    qualification: str = ""
    age: str = ""
    salary: str = ""
    pay_level: str = ""
    vacancies: str = ""
    state: str = ""
    location: str = ""
    category: str = ""          # Job / Exam / Apprenticeship / Internship
    application_start: str = "" # ISO date or free text
    application_end: str = ""
    exam_date: str = ""
    result_date: str = ""
    official_website: str = ""
    official_pdf: str = ""
    apply_link: str = ""
    selection_process: str = ""
    application_fee: str = ""
    status: str = "Not Applied"
    verification_status: str = "Unverified"
    verification_source: str = ""
    verification_timestamp: str = ""
    confidence: float = 0.0
    priority: str = "Low"
    notes: str = ""
    tags: str = ""
    first_seen: str = ""
    last_checked: str = ""

    def __post_init__(self):
        if not self.notification_id:
            self.notification_id = self.make_id()
        if not self.first_seen:
            self.first_seen = datetime.now().isoformat(timespec="seconds")
        self.last_checked = datetime.now().isoformat(timespec="seconds")

    def make_id(self):
        # an advertisement number is the strongest identity - it merges the
        # same notification found via different sources/titles
        advt = re.search(r"([A-Z]{2,12}\s?[:/]\s?[A-Z]{0,6}\s?[:/]?\s?\d{1,3}\s?[:/]\s?\d{4})",
                         self.job_name + " " + self.notes, re.I)
        if advt:
            key = re.sub(r"\s+", "", advt.group(1).lower())
        else:
            key = re.sub(r"\s+", " ", (self.job_name + self.organization).lower()).strip()
        return hashlib.sha1(key.encode()).hexdigest()[:12]

    def end_date(self):
        """Parse application_end into a date if possible."""
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", self.application_end)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None

    def days_left(self, today=None):
        d = self.end_date()
        if d is None:
            return None
        return (d - (today or date.today())).days

    def to_dict(self):
        return asdict(self)
