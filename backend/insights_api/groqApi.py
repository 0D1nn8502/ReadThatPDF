from rate_limiting.RateLimiter import LLMRateLimiter  
from typing import Optional, Tuple, Dict, Any, Union 
from groq import AsyncGroq 
from dotenv import load_dotenv 
import os 
from fastapi import HTTPException 

load_dotenv() 

## What does using async groq mean for my use case? ## 
## Generate insights from given text (perhaps later based on user_instructions) ## 

system_prompt = "Given some text, elaborate and explain it without jargon. If applicable, recommend concepts to brush up on " \
"and additional resources for comprehensive understanding. Complete the response within the max token limit." 



async def Generate_groq_insight(
    text: str,
    rate_limiter: LLMRateLimiter,
    system_prompt: str, 
    model: str = "openai/gpt-oss-120b",
    max_tokens: int = 1400,
) -> Tuple[str, Dict[str, Any]]: 
    
    """
    Generates an AI-powered explanation of the input text using the Groq API.

    Args:
        text (str): The input text to analyze.
        rate_limiter (LLMRateLimiter): Rate limiter instance to enforce API usage limits.
        system_prompt (str): The system prompt to guide the assistant's behavior.
        model (str): The model to use (default: 'openai/gpt-oss-120b').
        max_tokens (int): Maximum number of tokens in the output.

    Returns:
        Tuple[str, Dict[str, Any]]: Assistant's insight and token usage metadata.

    Raises:
        HTTPException(429): If rate limiter denies the request.
        HTTPException(500): If API key is missing.
        ValueError: If Groq API returns invalid or incomplete data.
    """

    # Rate limit check
    can_process = await rate_limiter.can_process_request(text)
    if not can_process["allowed"]:
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail=can_process["reason"]
        )

    # Ensure API key exists
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,  # Internal Server Error
            detail="Missing GROQ_API_KEY in environment variables"
        )

    # Call Groq API
    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        model=model,
        max_tokens=max_tokens
    )

    # Validate insight
    insight = response.choices[0].message.content
    if insight is None:
        raise ValueError("No content returned in response.")

    # Validate usage data
    usage = response.usage
    if usage is None:
        raise ValueError("Usage data unavailable")

    usage_data = {
        "total_tokens": usage.total_tokens,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens
    }

    return (insight, usage_data)


