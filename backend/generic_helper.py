# generic_helper.py

import re
import logging

logger = logging.getLogger(__name__)


def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
    return result


def extract_session_id(session_str: str):
    try:
        logger.info(f"Extracting session ID from: {session_str}")
        # Handle Dialogflow ES and Messenger format (projects/.../sessions/SESSION_ID)
        match = re.search(r'sessions/([^/]+)', session_str)
        if match:
            session_id = match.group(1)
            logger.info(f"Extracted session ID: {session_id}")
            return session_id

        # Fallback for unexpected formats
        parts = session_str.split('/')
        session_id = parts[-1] if parts else ""
        logger.warning(f"Fallback extraction, session ID: {session_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error extracting session ID from {session_str}: {e}")
        return ""