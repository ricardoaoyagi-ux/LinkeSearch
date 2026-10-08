from datetime import datetime, timedelta, timezone

from app.models.job import ScrapedJob
from app.scraping import parsers
from app.scraping.linkedin_client import build_search_url
from app.scraping.rsc import rsc_to_html

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def test_parse_card_unviewed_with_posted_time():
    raw = {
        "id": "111",
        "ps": [
            "Tech Lead Java (Verified job)\nTech Lead Java",
            "ACME Bank",
            "Osasco, SP (Hybrid)",
            "2 connections work here",
            "Posted 2 hours ago\n2 hours ago",
            "·",
            "Be an early applicant",
            "·",
            "Easy Apply",
        ],
        "hidden_title": "Tech Lead Java",
    }
    job = parsers.parse_card(raw, NOW)
    assert job.title == "Tech Lead Java"
    assert job.company == "ACME Bank"
    assert job.location == "Osasco, SP"
    assert job.workplace_type == "Hybrid"
    assert job.posted_at == NOW - timedelta(hours=2)
    assert job.posted_label == "2 hours ago"
    assert not job.li_viewed and not job.li_applied
    assert job.is_easy_apply is True
    assert job.job_url == "https://www.linkedin.com/jobs/view/111/"


def test_parse_card_viewed_and_applied_hide_posted_time():
    viewed = parsers.parse_card({"id": "1", "ps": ["T", "C", "L", "Viewed", "·", "x"]}, NOW)
    assert viewed.li_viewed and not viewed.li_applied and viewed.posted_at is None
    applied = parsers.parse_card({"id": "2", "ps": ["T", "C", "L", "Applied"]}, NOW)
    assert applied.li_applied and applied.li_viewed
    saved = parsers.parse_card({"id": "3", "ps": ["T", "C", "L", "Saved"]}, NOW)
    assert not saved.li_viewed


def test_parse_relative():
    assert parsers.parse_relative("Posted 26 minutes ago", NOW) == NOW - timedelta(minutes=26)
    assert parsers.parse_relative("Reposted 1 hour ago", NOW) == NOW - timedelta(hours=1)
    assert parsers.parse_relative("3 days ago", NOW) == NOW - timedelta(days=3)
    assert parsers.parse_relative("Viewed", NOW) is None
    assert parsers.relative_label("Reposted 1 hour ago") == "Reposted 1 hour ago"


def test_unwrap_safety_url():
    href = "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fjobs%2Eexample%2Ecom%2Fx%3Fid%3D1&urlhash=a"
    assert parsers.unwrap_safety_url(href) == "https://jobs.example.com/x?id=1"
    assert parsers.unwrap_safety_url("javascript:alert(1)") is None
    assert parsers.unwrap_safety_url(None) is None


def test_parse_job_page_and_apply_detail():
    page = (
        '<p><span><strong>Reposted 5 hours ago</strong></span></p>'
        '<a aria-disabled="false" href="https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fats%2Eexample%2Ecom%2F9'
        '&amp;urlhash=x" target="_blank" aria-label="Apply on company website">Apply</a>'
    )
    detail = parsers.parse_job_page(page)
    assert detail["posted_text"] == "Reposted 5 hours ago"
    job = ScrapedJob(job_id="9", title="T", job_url="https://www.linkedin.com/jobs/view/9/")
    full = parsers.apply_detail(job, {**detail, "about_html": "<p>x</p>"}, NOW)
    assert full.apply_url == "https://ats.example.com/9"
    assert full.is_easy_apply is False
    assert full.posted_at == NOW - timedelta(hours=5)
    assert full.about_html == "<p>x</p>"

    easy = parsers.apply_detail(job, parsers.parse_job_page("<div>nothing</div>"), NOW)
    assert easy.is_easy_apply is True and easy.apply_url == job.job_url


def test_parse_search_link():
    href = "https://www.linkedin.com/jobs/search-results/?keywords=Senior+Lead%2C+remote&origin=PREFERENCES&geoId=104"
    assert parsers.parse_search_link(href) == ("Senior Lead, remote", "104")
    assert parsers.parse_search_link("https://www.linkedin.com/jobs/search/?geoId=1") is None


def test_build_search_url():
    url = build_search_url("Tech Lead", "104", 36, start=25)
    assert "f_TPR=r129600" in url and "start=25" in url and "keywords=Tech+Lead" in url and "geoId=104" in url


def test_rsc_to_html():
    stream = "\n".join(
        [
            '1:"abc"',
            '2:I["$1",[],"default"]',
            '3:"$Sreact.fragment"',
            '4:["$","li",null,{"children":"Second <b>"}]',
            '0:["$","$L2",null,{"children":[["$","h2",null,{"children":["About the job"]}],'
            '["$","$L2",null,{"textProps":{"children":[["$","strong","k",{"children":"Hello"}],["$","br",null,{}],'
            '["$","ul",null,{"className":"x","children":[["$","li",null,{"children":"First"}],"$4"]}],'
            '["$","button",null,{"children":"more"}],"$$5 off"]}}]]}]',
        ]
    )
    assert rsc_to_html(stream) == "<strong>Hello</strong><br><ul><li>First</li><li>Second &lt;b&gt;</li></ul>$5 off"
