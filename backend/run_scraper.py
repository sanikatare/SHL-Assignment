#!/usr/bin/env python3
"""Script to run the SHL catalog scraper."""
import logging
import sys
from scraper import SHLScraper
from utils import setup_logging
from dotenv import load_dotenv

load_dotenv()

logger = setup_logging()


def main():
    """Run scraper and save catalog."""
    logger.info("=" * 60)
    logger.info("SHL Assessment Catalog Scraper")
    logger.info("=" * 60)
    
    try:
        scraper = SHLScraper()
        logger.info("Starting catalog scrape...")
        
        assessments = scraper.scrape()
        
        logger.info(f"Scraped {len(assessments)} unique assessments")
        
        if not assessments:
            logger.warning("No assessments scraped. Check internet connection and SHL website availability.")
            return 1
        
        success = scraper.save("catalog.json")
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info(f"SUCCESS: Catalog saved to catalog.json")
            logger.info(f"Total assessments: {len(assessments)}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("Failed to save catalog")
            return 1
    
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
