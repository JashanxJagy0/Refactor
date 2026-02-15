"""
AI chat service integration
Supports both Perplexity AI (paid) and g4f (free)
"""
import logging
from typing import Optional, List, Dict
from openai import OpenAI
import g4f
from config import PERPLEXITY_API_KEY

# Initialize Perplexity client
perplexity_client = None
if PERPLEXITY_API_KEY and PERPLEXITY_API_KEY != "[REDACTED]":
    try:
        perplexity_client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )
    except Exception as e:
        logging.error(f"Failed to initialize Perplexity client: {e}")


async def chat_with_ai(messages: List[Dict[str, str]], use_free: bool = False) -> Optional[str]:
    """
    Send messages to AI and get response
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        use_free: If True, use free g4f instead of Perplexity
        
    Returns:
        AI response text or None on error
    """
    if use_free:
        return await chat_with_g4f(messages)
    else:
        return await chat_with_perplexity(messages)


async def chat_with_perplexity(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Chat using Perplexity AI (paid)
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        
    Returns:
        AI response text or None on error
    """
    if not perplexity_client:
        logging.warning("Perplexity client not initialized")
        return None
    
    try:
        response = perplexity_client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Perplexity API error: {e}")
        return None


async def chat_with_g4f(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Chat using g4f (free)
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        
    Returns:
        AI response text or None on error
    """
    try:
        response = await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response
    except Exception as e:
        logging.error(f"g4f API error: {e}")
        return None


def format_chat_context(user_message: str, context: Optional[List[Dict]] = None) -> List[Dict[str, str]]:
    """
    Format chat messages for AI API
    
    Args:
        user_message: The user's current message
        context: Optional list of previous messages for context
        
    Returns:
        Formatted messages list
    """
    messages = []
    
    # Add system message
    messages.append({
        "role": "system",
        "content": "You are a helpful AI assistant for a casino bot. Be concise and friendly."
    })
    
    # Add context if provided
    if context:
        messages.extend(context)
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages
