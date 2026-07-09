"""Eligibility, location and spam filters."""
import re

CENTRAL_MARKERS = [
    "central", "all india", "psu", "isro", "drdo", "ssc", "upsc", "rrb", "railway",
    "ibps", "sbi", "rbi", "lic", "nabard", "fci", "bel", "hal", "bhel", "barc",
    "npcil", "ecil", "bsnl", "iocl", "ongc", "gail", "sail", "hpcl", "bpcl",
    "army", "navy", "air force", "coast guard", "gate", "ugc", "csir", "nic",
    "nielit", "cdac", "nal", "nhai", "epfo", "esic", "india post", "post office",
]


def _text(n):
    return " ".join([
        n.job_name, n.exam_name, n.department, n.organization, n.qualification,
        n.state, n.location, n.tags, n.notes,
    ]).lower()


NAV_NOISE = {
    "recruitments", "recruitment (cens)", "recruitment exams", "district-recruitment",
    "active examinations", "forthcoming examinations", "online recruitment application (ora)",
    "recruitment tests", "recruitment requisition", "recruitment advertisements",
    "examination notifications", "crp - clerks", "crp - po/mts", "crp - specialist officers",
    "crp clerical cadre", "crp specialist officer", "crp csa(customer service associates)",
    "crp specialist officers", "personnel selection services for recruitment, promotion and placement",
    "government of india, ministry of railways railway recruitment board",
    "status of recruitment cases (advertisement-wise)",
    "status of lateral recruitment cases (advertisement-wise)",
    "recruitment cases kept on hold on account of pending litigations",
}


def is_nav_noise(n):
    """Menu links and site chrome scraped by accident - not real notifications."""
    name = n.job_name.lower()
    for prefix in ("upsc:", "ssc:", "ibps:", "rrb:", "kea:"):
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
    if name in NAV_NOISE:
        return True
    # a real notification names a post, year or advertisement
    import re
    return len(name) < 22 and not re.search(r"\d{4}", name)


def is_spam(n, cfg):
    t = _text(n)
    return any(k in t for k in cfg["filters"]["exclude_keywords"]) or is_nav_noise(n)


def experience_ok(n, cfg):
    t = _text(n)
    m = re.search(r"(\d+)\s*(?:\+|-\d+)?\s*(?:years?|yrs?)\s*(?:of\s*)?experience", t)
    if m and int(m.group(1)) > cfg["filters"]["max_experience_years"]:
        return False
    return True


def qualification_ok(n, cfg):
    if not n.qualification:
        return True  # unknown, keep and let verification sort it
    t = n.qualification.lower()
    quals = cfg["filters"]["qualifications"] + cfg["filters"]["branches"]
    return any(q in t for q in quals) or "phd" not in t.split()[0:1]


def location_ok(n, cfg):
    t = _text(n)
    if any(m in t for m in CENTRAL_MARKERS):
        return True
    states = ["andhra", "telangana", "tamil nadu", "kerala", "maharashtra", "gujarat",
              "rajasthan", "punjab", "haryana", "bihar", "odisha", "west bengal",
              "uttar pradesh", "madhya pradesh", "assam", "jharkhand", "chhattisgarh",
              "uttarakhand", "himachal", "goa", "delhi"]
    mentions_other_state_govt = any(
        s in t and ("state govern" in t or "public service commission" in t or "psc" in t)
        for s in states)
    if "karnataka" in t:
        return True
    return not mentions_other_state_govt


def relevant(n, cfg):
    t = _text(n)
    return any(k in t for k in cfg["filters"]["track_keywords"])


def passes(n, cfg):
    return (relevant(n, cfg) and not is_spam(n, cfg)
            and experience_ok(n, cfg) and location_ok(n, cfg)
            and qualification_ok(n, cfg))
