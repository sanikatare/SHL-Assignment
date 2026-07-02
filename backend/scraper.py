"""Scrape the SHL Individual Test Solutions product catalog.

The live catalog lives at https://www.shl.com/products/product-catalog/ and
is server-side rendered (no JS execution needed) with query-string
pagination: `?start=<offset>&type=1` where `type=1` restricts results to
"Individual Test Solutions" (type=2 is "Pre-packaged Job Solutions", which
is explicitly out of scope for this assignment) and each page returns 12
rows.

Each row in the listing table gives us: name, detail-page URL, a Remote
Testing indicator, an Adaptive/IRT indicator, and one or more Test Type
letter codes (from the legend: A=Ability & Aptitude, B=Biodata & SJT,
C=Competencies, D=Development & 360, E=Assessment Exercises,
K=Knowledge & Skills, P=Personality & Behavior, S=Simulations).

Optionally (SCRAPE_DETAILS=true) the scraper will also visit each
assessment's own detail page to pull a real description/duration, at the
cost of one extra request per assessment (~370+ extra requests).
"""
import logging
import re
import time
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils import save_catalog, get_env_or_default

logger = logging.getLogger(__name__)

TEST_TYPE_LEGEND = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


class SHLScraper:
    """Scrape the real, paginated SHL Individual Test Solutions catalog."""

    BASE_URL = "https://www.shl.com"
    CATALOG_URL = "https://www.shl.com/products/product-catalog/"
    PAGE_SIZE = 12
    INDIVIDUAL_TEST_SOLUTIONS_TYPE = 1  # type=2 would be Pre-packaged Job Solutions (out of scope)

    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        retry_delay: int = None,
        scrape_details: bool = None,
    ):
        """Initialize scraper with configuration."""
        self.timeout = timeout or int(get_env_or_default("SCRAPER_TIMEOUT", 30))
        self.max_retries = max_retries or int(get_env_or_default("SCRAPER_MAX_RETRIES", 3))
        self.retry_delay = retry_delay or int(get_env_or_default("SCRAPER_RETRY_DELAY", 2))
        self.scrape_details = (
            scrape_details
            if scrape_details is not None
            else get_env_or_default("SCRAPE_DETAILS", "false").lower() == "true"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })
        self.assessments: List[Dict[str, Any]] = []

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape every page of the Individual Test Solutions catalog."""
        logger.info("Starting SHL Individual Test Solutions catalog scrape")

        start = 0
        page_num = 1
        seen_urls = set()

        while True:
            url = f"{self.CATALOG_URL}?start={start}&type={self.INDIVIDUAL_TEST_SOLUTIONS_TYPE}"
            html = self._fetch_with_retry(url)
            if not html:
                logger.warning(f"Failed to fetch page at start={start}; stopping pagination")
                break

            rows = self._parse_listing_page(html)
            if not rows:
                logger.info(f"No rows found at start={start}; assuming end of catalog")
                break

            new_rows = 0
            for row in rows:
                if row["url"] in seen_urls:
                    continue
                seen_urls.add(row["url"])
                self.assessments.append(row)
                new_rows += 1

            logger.info(f"Page {page_num} (start={start}): {new_rows} new assessments "
                        f"(total so far: {len(self.assessments)})")

            if len(rows) < self.PAGE_SIZE:
                # Short page = last page.
                break

            start += self.PAGE_SIZE
            page_num += 1
            time.sleep(0.3)

            # Safety valve in case pagination never terminates.
            if page_num > 100:
                logger.warning("Exceeded 100 pages; stopping as a safety measure")
                break

        if self.scrape_details:
            self._enrich_with_details()

        logger.info(f"Scraped {len(self.assessments)} unique Individual Test Solutions")
        return self.assessments

    def _parse_listing_page(self, html: str) -> List[Dict[str, Any]]:
        """Parse one catalog listing page into row dicts."""
        soup = BeautifulSoup(html, "html.parser")
        rows_out = []

        # The catalog page can contain up to two tables (Pre-packaged Job
        # Solutions and Individual Test Solutions). We only want the table
        # whose header says "Individual Test Solutions".
        for table in soup.find_all("table"):
            header_text = table.get_text(" ", strip=True)[:60].lower()
            if "individual test solutions" not in header_text:
                continue

            for tr in table.find_all("tr"):
                link = tr.find("a", href=True)
                if not link:
                    continue

                name = link.get_text(strip=True)
                href = link["href"]
                if not name or "/product-catalog/view/" not in href:
                    continue

                full_url = urljoin(self.BASE_URL, href)

                cells = tr.find_all("td")
                remote_support = self._cell_has_indicator(cells[1]) if len(cells) > 1 else False
                adaptive_irt = self._cell_has_indicator(cells[2]) if len(cells) > 2 else False
                test_type_text = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""
                test_type_codes = test_type_text.split()

                rows_out.append({
                    "name": name,
                    "url": full_url,
                    "description": self._default_description(name, test_type_codes),
                    "category": self._category_from_codes(test_type_codes),
                    "assessment_type": self._assessment_type_from_codes(test_type_codes),
                    "test_type": " ".join(test_type_codes),
                    "skills_measured": self._keywords_from_name(name),
                    "duration": "",
                    "remote_testing_support": remote_support,
                    "adaptive_irt_support": adaptive_irt,
                    "keywords": self._keywords_from_name(name),
                })

        return rows_out

    @staticmethod
    def _cell_has_indicator(cell) -> bool:
        """Detect a Yes/checkmark indicator cell (SHL renders these as icons/CSS, not text)."""
        if cell is None:
            return False
        classes = " ".join(cell.get("class", [])).lower()
        if "yes" in classes or "circle" in classes or "check" in classes:
            return True
        text = cell.get_text(strip=True).lower()
        return text in ("yes", "y", "true", "\u2713")

    @staticmethod
    def _category_from_codes(codes: List[str]) -> str:
        if not codes:
            return "General Assessment"
        return TEST_TYPE_LEGEND.get(codes[0], "General Assessment")

    @staticmethod
    def _assessment_type_from_codes(codes: List[str]) -> str:
        names = [TEST_TYPE_LEGEND.get(c, c) for c in codes]
        return ", ".join(names) if names else "Assessment"

    @staticmethod
    def _keywords_from_name(name: str) -> List[str]:
        cleaned = re.sub(r"\(new\)", "", name, flags=re.IGNORECASE)
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9\+\#\.]*", cleaned)
        return [t.lower() for t in tokens if len(t) > 1]

    @staticmethod
    def _default_description(name: str, codes: List[str]) -> str:
        type_desc = ", ".join(TEST_TYPE_LEGEND.get(c, c) for c in codes) or "assessment"
        return f"SHL {name} — an Individual Test Solution in the {type_desc} category."

    def _enrich_with_details(self) -> None:
        """Optionally visit each detail page for a real description/duration (slow)."""
        logger.info(f"Enriching {len(self.assessments)} assessments with detail-page data "
                     "(this can take a while)")
        for idx, item in enumerate(self.assessments):
            html = self._fetch_with_retry(item["url"])
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            meta_desc = soup.find("meta", {"name": "description"}) or soup.find(
                "meta", {"property": "og:description"}
            )
            if meta_desc and meta_desc.get("content"):
                item["description"] = meta_desc["content"][:500]

            page_text = soup.get_text()
            duration_match = re.search(
                r"(\d+\s*(?:to|-)\s*\d+\s*(?:minutes|mins)|\d+\s*(?:minutes|mins))",
                page_text, re.IGNORECASE
            )
            if duration_match:
                item["duration"] = duration_match.group(1)

            if (idx + 1) % 25 == 0:
                logger.info(f"  ...enriched {idx + 1}/{len(self.assessments)}")
            time.sleep(0.3)

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.debug(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        logger.warning(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None

    def save(self, output_path: str = "catalog.json") -> bool:
        """Save scraped catalog to JSON."""
        return save_catalog(self.assessments, output_path)
