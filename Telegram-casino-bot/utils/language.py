"""
Language management and translation utilities
"""
import os
import logging
from typing import Optional, Dict
from config import LANGUAGE_FILES

# Default language
DEFAULT_LANG = "en"

# Language cache to avoid repeated file reads
_language_cache = {}

# Main language dictionary (will be populated at startup)
LANGUAGES = {}


def load_language_file(lang_code: str) -> Optional[Dict[str, str]]:
    """Load a language file and return as a dictionary"""
    if lang_code in _language_cache:
        return _language_cache[lang_code]
    
    filename = LANGUAGE_FILES.get(lang_code)
    if not filename:
        return None
    
    # Look for language files in the languages/ directory
    filepath = os.path.join("languages", filename)
    if not os.path.exists(filepath):
        logging.warning(f"Language file not found: {filepath}")
        return None
    
    lang_dict = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            current_key = None
            current_value = []
            
            for line in f:
                line_rstrip = line.rstrip('\n')
                
                # Skip comments and empty lines when not in a multi-line value
                if not current_key and (not line_rstrip or line_rstrip.startswith('#')):
                    continue
                
                # Check for new key = "value" pattern
                if ' = "' in line_rstrip and not current_key:
                    parts = line_rstrip.split(' = "', 1)
                    if len(parts) == 2:
                        current_key = parts[0].strip()
                        value_part = parts[1]
                        
                        # Check if value ends on this line
                        if value_part.endswith('"'):
                            lang_dict[current_key] = value_part[:-1]
                            current_key = None
                            current_value = []
                        else:
                            current_value = [value_part]
                elif current_key:
                    # Continuation of multi-line value
                    if line_rstrip.endswith('"'):
                        current_value.append(line_rstrip[:-1])
                        lang_dict[current_key] = '\n'.join(current_value)
                        current_key = None
                        current_value = []
                    else:
                        current_value.append(line_rstrip)
        
        _language_cache[lang_code] = lang_dict
        logging.info(f"Loaded language file: {filename} with {len(lang_dict)} entries")
        return lang_dict
    except Exception as e:
        logging.error(f"Error loading language file {filename}: {e}")
        return None


def load_language_files():
    """Load all language files at startup into the global LANGUAGES dictionary"""
    global LANGUAGES
    for lang_code, filename in LANGUAGE_FILES.items():
        lang_dict = load_language_file(lang_code)
        if lang_dict:
            # Merge with existing LANGUAGES dict (file takes precedence)
            if lang_code in LANGUAGES:
                LANGUAGES[lang_code].update(lang_dict)
            else:
                LANGUAGES[lang_code] = lang_dict
            logging.info(f"Loaded {len(lang_dict)} translations for {lang_code}")
        else:
            logging.warning(f"Failed to load language file for {lang_code}")


def get_text(user_id_or_key, key_or_lang=None, **kwargs) -> str:
    """
    Get translated text based on user's language preference.
    
    Supports two call signatures for backward compatibility:
    1. get_text(user_id, key, **kwargs) - New preferred signature (user_id can be int or None)
    2. get_text(key, lang_code, **kwargs) - Legacy signature (both are strings)
    
    Args:
        user_id_or_key: Either user_id (int/None) or translation key (str)
        key_or_lang: Either translation key (str) or language code (str), or None
        **kwargs: Format arguments for string formatting
        
    Returns:
        Formatted translated string with fallback to English
    """
    from core.state import user_stats  # Import here to avoid circular dependency
    
    # Determine which signature is being used based on type
    if isinstance(user_id_or_key, (int, type(None))):
        # New signature: get_text(user_id, key, **kwargs)
        user_id = user_id_or_key
        key = key_or_lang
        # Get language from user_id, using DEFAULT_LANG only if user_id is explicitly None
        if user_id is not None:
            lang_code = user_stats.get(user_id, {}).get("userinfo", {}).get("language", DEFAULT_LANG)
        else:
            lang_code = DEFAULT_LANG
    else:
        # Legacy signature: get_text(key, lang_code, **kwargs)
        key = user_id_or_key
        lang_code = key_or_lang if key_or_lang else DEFAULT_LANG
    
    # Ensure lang_code is valid
    lang_code = lang_code if lang_code in LANGUAGE_FILES else DEFAULT_LANG
    
    # Try to get text from LANGUAGES dict
    if lang_code in LANGUAGES and key in LANGUAGES[lang_code]:
        text = LANGUAGES[lang_code][key]
    elif key in LANGUAGES.get(DEFAULT_LANG, {}):
        text = LANGUAGES[DEFAULT_LANG][key]
    else:
        logging.warning(f"Missing translation key: '{key}'")
        return f"Missing translation for '{key}'"
    
    # Format the text with provided kwargs
    try:
        return text.format(**kwargs)
    except KeyError as e:
        logging.warning(f"Missing format key {e} in text '{key}' for language '{lang_code}'")
        return text
