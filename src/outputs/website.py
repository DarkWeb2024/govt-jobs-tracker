"""Builds the GitHub Pages site into the configured site directory."""
import os
import shutil

from .tabular import write_json, write_rss


def build_site(notifications, site_dir, template="site/index.html",
               site_url="https://darkweb2024.github.io/govt-jobs-tracker/"):
    os.makedirs(os.path.join(site_dir, "data"), exist_ok=True)
    shutil.copyfile(template, os.path.join(site_dir, "index.html"))
    write_json(notifications, os.path.join(site_dir, "data.json"))
    write_rss(notifications, os.path.join(site_dir, "feed.xml"), site_url)
    # .nojekyll lets Pages serve everything as-is
    open(os.path.join(site_dir, ".nojekyll"), "w").close()
    return site_dir
