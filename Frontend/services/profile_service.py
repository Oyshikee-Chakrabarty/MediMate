"""Profile service for storing, caching, and updating user profile vitals.

Stores extra health profile fields like blood group, age, gender, weight,
height, emergency contact, allergies, and chronic conditions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
_PROFILE_FILE: Path = _DATA_DIR / "user_profiles.json"

DEFAULT_PROFILE: Dict[str, Any] = {
    "blood_group": "O+",
    "age": "28",
    "gender": "Male",
    "weight": "68 kg",
    "height": "172 cm",
    "emergency_contact": "+880 1712-345678",
    "allergies": "None",
    "conditions": "None",
}


def _ensure_dir() -> None:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.debug("Failed creating profile data directory: %s", exc)


def load_all_profiles() -> Dict[str, Dict[str, Any]]:
    _ensure_dir()
    if not _PROFILE_FILE.exists():
        return {}
    try:
        with open(_PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.debug("Failed reading profiles json: %s", exc)
        return {}


def save_all_profiles(profiles: Dict[str, Dict[str, Any]]) -> None:
    _ensure_dir()
    try:
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.debug("Failed writing profiles json: %s", exc)


def get_user_profile(user_key: str) -> Dict[str, Any]:
    """Retrieve profile vitals for a user (keyed by user ID or email)."""
    if not user_key:
        return dict(DEFAULT_PROFILE)
    profiles = load_all_profiles()
    res = dict(DEFAULT_PROFILE)
    if user_key in profiles:
        res.update(profiles[user_key])
    return res


def update_user_profile(user_key: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update profile vitals for a user and persist to disk."""
    if not user_key:
        return profile_data
    profiles = load_all_profiles()
    current = profiles.get(user_key, dict(DEFAULT_PROFILE))
    current.update(profile_data)
    profiles[user_key] = current
    save_all_profiles(profiles)
    return current
