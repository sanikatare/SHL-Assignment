"""Utility functions for the application."""
import logging
import json
from pathlib import Path
from typing import Any, Dict, List
import os
from dotenv import load_dotenv

load_dotenv()


def setup_logging(log_level: str = None) -> logging.Logger:
    """Configure logging for the application."""
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def load_catalog(catalog_path: str = "catalog.json") -> List[Dict[str, Any]]:
    """Load assessment catalog from JSON file."""
    logger = logging.getLogger(__name__)
    
    if not Path(catalog_path).exists():
        logger.warning(f"Catalog file not found at {catalog_path}")
        return []
    
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        logger.info(f"Loaded catalog with {len(catalog)} assessments")
        return catalog
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse catalog JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")
        return []


def save_catalog(catalog: List[Dict[str, Any]], catalog_path: str = "catalog.json") -> bool:
    """Save assessment catalog to JSON file."""
    logger = logging.getLogger(__name__)
    
    try:
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved catalog with {len(catalog)} assessments")
        return True
    except Exception as e:
        logger.error(f"Failed to save catalog: {e}")
        return False


def extract_constraints(text: str) -> Dict[str, List[str]]:
    """Extract hiring constraints from user text."""
    constraints = {
        "role": [],
        "experience": [],
        "industry": [],
        "skills": [],
        "personality": [],
        "leadership": [],
        "technical": [],
        "language": [],
        "coding": [],
        "sales": [],
        "customer_support": []
    }
    
    text_lower = text.lower()
    
    # Role extraction
    role_keywords = {
        "manager": ["manager", "team lead", "supervisor", "director", "leader"],
        "developer": ["developer", "engineer", "programmer", "coder"],
        "sales": ["sales", "account executive", "business development", "sales rep"],
        "support": ["support", "customer service", "helpdesk", "agent"],
        "analyst": ["analyst", "data analyst", "business analyst"],
        "hr": ["hr", "human resources", "recruiter"],
        "trainer": ["trainer", "training"],
    }
    
    for role, keywords in role_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if role not in constraints["role"]:
                    constraints["role"].append(role)
    
    # Experience extraction
    experience_keywords = {
        "junior": ["junior", "entry level", "graduate", "0-2 years", "entry-level"],
        "mid": ["mid", "intermediate", "3-5 years"],
        "senior": ["senior", "expert", "5+ years", "10+ years"],
    }
    
    for exp, keywords in experience_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if exp not in constraints["experience"]:
                    constraints["experience"].append(exp)
    
    # Skill extraction
    skill_keywords = {
        "leadership": ["leadership", "leading", "team management", "management"],
        "communication": ["communication", "interpersonal", "soft skills"],
        "analytical": ["analytical", "problem solving", "critical thinking"],
        "technical": ["technical", "programming", "coding"],
        "personality": ["personality", "traits", "behavioral"],
    }
    
    for skill, keywords in skill_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if skill not in constraints["skills"]:
                    constraints["skills"].append(skill)
    
    # Specific constraint extraction
    if "sales" in text_lower:
        if "sales" not in constraints["sales"]:
            constraints["sales"].append("sales")
    
    if "language" in text_lower or "language skill" in text_lower:
        constraints["language"].append("language")
    
    if "coding" in text_lower or "programming" in text_lower:
        constraints["coding"].append("coding")
    
    if "customer" in text_lower:
        constraints["customer_support"].append("customer_support")
    
    return {k: list(set(v)) for k, v in constraints.items() if v}


def get_env_or_default(key: str, default: Any = None) -> Any:
    """Get environment variable or return default value."""
    return os.getenv(key, default)
