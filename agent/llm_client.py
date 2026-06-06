"""LLM Client - Unified interface for multiple LLM providers."""
import os
from typing import List, Dict, Optional


def call_llm(messages: List[Dict], system_prompt: str, config, temperature: float = 0.2) -> str:
    """Call LLM with unified interface across multiple providers.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        system_prompt: System prompt string
        config: Configuration module with LLM_PROVIDER and API keys
        temperature: Temperature for generation (0.0-1.0)
        
    Returns:
        Generated text response
        
    Raises:
        ValueError: If API key not set or provider not supported
        Exception: If API call fails
    """
    provider = config.LLM_PROVIDER
    
    if provider == "groq":
        return _call_groq(messages, system_prompt, config, temperature)
    elif provider == "anthropic":
        return _call_anthropic(messages, system_prompt, config, temperature)
    elif provider == "openai":
        return _call_openai(messages, system_prompt, config, temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _call_groq(messages: List[Dict], system_prompt: str, config, temperature: float) -> str:
    """Call Groq API."""
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("groq package not installed. Run: pip install groq")
    
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    client = Groq(api_key=config.GROQ_API_KEY)
    
    all_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=all_messages,
        temperature=temperature
    )
    
    return response.choices[0].message.content.strip()


def _call_anthropic(messages: List[Dict], system_prompt: str, config, temperature: float) -> str:
    """Call Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
        temperature=temperature
    )
    
    return response.content[0].text


def _call_openai(messages: List[Dict], system_prompt: str, config, temperature: float) -> str:
    """Call OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")
    
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    all_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=all_messages,
        temperature=temperature
    )
    
    return response.choices[0].message.content.strip()


def get_llm_client(config):
    """Get LLM client instance for providers that need it.
    
    This is for backward compatibility with code that expects a client object.
    
    Args:
        config: Configuration module
        
    Returns:
        Client instance (Groq) or None for other providers
    """
    if config.LLM_PROVIDER == "groq":
        from groq import Groq
        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set")
        return Groq(api_key=config.GROQ_API_KEY)
    else:
        # For anthropic and openai, we don't need to return a client
        return None
