"""Core unit tests: identity, filters, verification, priority, storage.

Run with:  python -m unittest discover tests -v
"""
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Notification, is_applied
from src import filters, priority, verify
from src.database import Store


def note(**kw):
    base = dict(job_name="SSC CGL 2026 Combined Graduate Level Examination",
                organization="SSC", category="Exam")
    base.update(kw)
    return Notification(**base)


CFG = {
    "filters": {
        "qualifications": ["10th pass", "12th pass", "diploma", "iti", "graduate",
                           "b.e", "b.tech", "any graduate", "b.sc", "bca"],
        "branches": ["cse", "ise", "ece", "ai", "ml"],
        "exclude_keywords": ["walk-in", "consultancy", "training fee", "franchise", "mlm"],
        "max_experience_years": 2,
        "allowed_states": ["karnataka", "all india", "central"],
        "track_keywords": ["recruitment", "cgl", "exam", "vacancy", "posts",
                           "notification", "apprentice", "technician"],
    }
}


class TestIdentity(unittest.TestCase):
    def test_advt_number_merges_different_titles(self):
        a = note(job_name="ISRO ISTRAC Recruitment 2026 (ISTRAC:02:2026) Technical posts")
        b = note(job_name="ISTRAC:02:2026: Recruitment to the posts of Technician B")
        self.assertEqual(a.notification_id, b.notification_id)

    def test_same_title_same_id(self):
        self.assertEqual(note().notification_id, note().notification_id)

    def test_different_jobs_differ(self):
        a = note(job_name="RRB Technician CEN 02/2026 Signal posts")
        b = note(job_name="RRB JE CEN 03/2026 Junior Engineer posts")
        self.assertNotEqual(a.notification_id, b.notification_id)


class TestAppliedStates(unittest.TestCase):
    def test_not_applied_is_not_applied(self):
        self.assertFalse(is_applied("Not Applied"))

    def test_applied_variants(self):
        for s in ("Applied", "Fee Paid", "Admit Card Available", "Already Applied"):
            self.assertTrue(is_applied(s), s)

    def test_terminal_states_not_counted(self):
        for s in ("Rejected", "Completed", "Result Declared"):
            self.assertFalse(is_applied(s), s)


class TestFilters(unittest.TestCase):
    def test_normal_notification_passes(self):
        self.assertTrue(filters.passes(note(state="All India"), CFG))

    def test_spam_keyword_rejected(self):
        n = note(job_name="Walk-in interview consultancy training fee recruitment 2026")
        self.assertFalse(filters.passes(n, CFG))

    def test_other_state_rejected(self):
        n = note(job_name="Kerala PSC LDC Recruitment 2026 notification",
                 organization="Kerala PSC", state="Kerala",
                 department="Kerala State Government")
        self.assertFalse(filters.passes(n, CFG))

    def test_karnataka_allowed(self):
        n = note(job_name="KEA Armed Police Constable Recruitment 2026",
                 organization="KEA", state="Karnataka")
        self.assertTrue(filters.passes(n, CFG))

    def test_experienced_only_rejected(self):
        n = note(job_name="NHAI Recruitment 2026 Manager posts",
                 qualification="B.E with minimum 10 years experience")
        self.assertFalse(filters.passes(n, CFG))


class TestVerify(unittest.TestCase):
    def test_official_pdf_highest(self):
        n = note(official_pdf="https://ssc.gov.in/notice/cgl2026.pdf",
                 official_website="https://ssc.gov.in/",
                 verification_source="official:ssc.gov.in")
        verify.apply(n)
        self.assertEqual(n.verification_status, "Verified with Official PDF")
        self.assertGreaterEqual(n.confidence, 0.9)

    def test_aggregator_only_stays_unverified(self):
        n = note(apply_link="https://www.freejobalert.com/some-job/",
                 verification_source="aggregator:freejobalert.com")
        verify.apply(n)
        self.assertEqual(n.verification_status, "Unverified")

    def test_registry_domain_counts_as_official(self):
        # canarabank.com is only official because organizations.json lists it
        self.assertTrue(verify.is_official("https://canarabank.com/careers"))

    def test_random_domain_not_official(self):
        self.assertFalse(verify.is_official("https://example.com/jobs"))

    def test_past_deadline_closes(self):
        n = note(application_end="2020-01-01",
                 official_website="https://ssc.gov.in/",
                 verification_source="official:ssc.gov.in")
        verify.apply(n)
        self.assertEqual(n.verification_status, "Application Closed")


class TestPriority(unittest.TestCase):
    def check(self, end, expected):
        n = note(application_end=end)
        priority.assign(n, today=date(2026, 7, 9))
        self.assertEqual(n.priority, expected)

    def test_tiers(self):
        self.check("2026-07-10", "Critical")   # 1 day
        self.check("2026-07-12", "Critical")   # 3 days
        self.check("2026-07-16", "High")       # 7 days
        self.check("2026-08-01", "Medium")     # 23 days
        self.check("2026-12-01", "Low")
        self.check("", "Low")


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.tmp, "t.db"))

    def test_upsert_new_then_unchanged(self):
        n = note()
        self.assertEqual(self.store.upsert(n), "new")
        self.assertIn(self.store.upsert(note()), ("unchanged", "updated"))
        self.assertEqual(len(self.store.all()), 1)

    def test_change_logged_to_history(self):
        self.store.upsert(note(vacancies="100"))
        self.store.upsert(note(vacancies="150"))
        rows = self.store.changes_since("1970-01-01")
        self.assertTrue(any(r[2] == "vacancies" and r[4] == "150" for r in rows))

    def test_status_protected_from_scraper(self):
        n = note()
        self.store.upsert(n)
        self.store.set_status(n.notification_id, "Applied")
        self.store.upsert(note())          # fresh scrape, status default Not Applied
        self.assertEqual(self.store.get(n.notification_id).status, "Applied")


if __name__ == "__main__":
    unittest.main()
