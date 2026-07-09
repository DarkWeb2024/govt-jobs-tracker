"""Maps config source flags to scraper callables."""
from . import isro, karnataka_hc, kea, central, aggregator


def enabled_scrapers(cfg):
    s = cfg["sources"]
    table = {
        "isro": isro.scrape,
        "karnataka_high_court": karnataka_hc.scrape,
        "kea": kea.scrape,
        "upsc": central.upsc,
        "ssc": central.ssc,
        "rrb": central.rrb,
        "ibps": central.ibps,
        "agnipath_vayu": central.agnipath_vayu,
        "employment_news": central.employment_news,
        "freejobalert": aggregator.scrape,
    }
    return {name: fn for name, fn in table.items() if s.get(name)}
