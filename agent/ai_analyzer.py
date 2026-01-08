"""
AI Analyzer - LLM-powered intelligent code analysis
Supports multiple LLM providers: Groq (FREE), Together AI, OpenRouter, Anthropic, etc.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """
    Uses LLM to analyze code and provide intelligent suggestions
    Supports multiple providers with automatic fallback
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        """
        Initialize with API key and provider
        
        Args:
            api_key: Optional API key (will check env vars if not provided)
            provider: Optional provider name ('groq', 'together', 'openrouter', 'anthropic')
                     If not specified, will auto-detect from available keys
        """
        # Detect provider and key
        self.provider, self.api_key = self._detect_provider(api_key, provider)
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            print("⚠️  AI features disabled: Set one of these environment variables:")
            print("   - GROQ_API_KEY (FREE - Recommended)")
            print("   - TOGETHER_API_KEY")
            print("   - OPENROUTER_API_KEY")
            print("   - ANTHROPIC_API_KEY")
        else:
            print(f"✓ Using {self.provider.upper()} for AI analysis")
    
    def _detect_provider(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        """Detect which provider to use based on available keys"""
        
        # If explicit key and provider given
        if api_key and provider:
            return provider.lower(), api_key
        
        # Priority order: Groq (free) > Together > OpenRouter > Anthropic
        providers = [
            ('groq', 'GROQ_API_KEY'),
            ('together', 'TOGETHER_API_KEY'),
            ('openrouter', 'OPENROUTER_API_KEY'),
            ('anthropic', 'ANTHROPIC_API_KEY'),
        ]
        
        # If provider specified, use that
        if provider:
            for p_name, env_var in providers:
                if p_name == provider.lower():
                    key = api_key or os.getenv(env_var)
                    return p_name, key
        
        # Auto-detect first available
        for p_name, env_var in providers:
            key = os.getenv(env_var)
            if key:
                return p_name, key
        
        return None, None
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> Optional[str]:
        """
        Call LLM with the given prompt
        Handles different providers automatically
        """
        if not self.enabled:
            return None
        
        try:
            if self.provider == 'groq':
                return self._call_groq(prompt, max_tokens)
            elif self.provider == 'together':
                return self._call_together(prompt, max_tokens)
            elif self.provider == 'openrouter':
                return self._call_openrouter(prompt, max_tokens)
            elif self.provider == 'anthropic':
                return self._call_anthropic(prompt, max_tokens)
            else:
                logger.warning(f"Unknown provider: {self.provider}")
                print(f"⚠️  Unknown provider: {self.provider}")
                return None
        except ImportError as e:
            logger.error(f"Missing dependency for {self.provider}: {e}")
            print(f"⚠️  Please install: pip install {self.provider}")
            return None
        except ConnectionError as e:
            logger.error(f"Network error calling {self.provider}: {e}")
            print(f"⚠️  Network error. Check your internet connection.")
            return None
        except Exception as e:
            logger.error(f"LLM call failed for {self.provider}: {e}", exc_info=True)
            print(f"⚠️  AI analysis failed: {str(e)[:100]}")
            return None
    
    def _call_groq(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call Groq API (FREE and FAST)"""
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            if not response or not response.choices:
                raise ValueError("Empty response from Groq API")
            
            return response.choices[0].message.content
        except ImportError:
            raise ImportError("groq package not installed")
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise ConnectionError(f"Groq rate limit exceeded: {e}")
            elif "api_key" in str(e).lower():
                raise ValueError(f"Invalid Groq API key: {e}")
            else:
                raise ConnectionError(f"Groq API error: {e}")
    
    def _call_together(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call Together AI API"""
        try:
            import requests
            
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "meta-llama/Llama-3-70b-chat-hf",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                }
            )
            
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️  Together AI error: {e}")
            return None
    
    def _call_openrouter(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call OpenRouter API"""
        try:
            import requests
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/agi-engineer",
                },
                json={
                    "model": "meta-llama/llama-3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                }
            )
            
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️  OpenRouter error: {e}")
            return None
    
    def _call_anthropic(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Call Anthropic Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
        except ImportError:
            print("⚠️  Install anthropic: pip install anthropic")
            return None
    
    def analyze_code_quality(self, code: str, filename: str) -> str:
        """
        Analyze code quality and suggest improvements
        Returns: Formatted string with suggestions
        """
        if not self.enabled:
            return ""
        
        prompt = f"""Analyze this Python code and provide improvement suggestions.
Focus on:
1. Poor variable/function names
2. Missing docstrings
3. Code complexity
4. Performance issues
5. Best practices

Be specific with line numbers and provide actionable suggestions.

Filename: {filename}

```python
{code[:2000]}  
```

Provide clear, numbered suggestions."""

        response = self._call_llm(prompt, max_tokens=1024)
        return response if response else ""
    
    def suggest_better_name(self, old_name: str, context: str, name_type: str = "variable") -> str:
        """
        Suggest a better variable/function name
        """
        if not self.enabled:
            return ""
        
        prompt = f"""Suggest a better {name_type} name for '{old_name}':

Context:
```python
{context[:500]}
```

Provide ONE suggested name and brief reason."""

        response = self._call_llm(prompt, max_tokens=100)
        return response if response else ""
    
    def generate_docstring(self, function_code: str, function_name: str) -> str:
        """Generate docstring for a function"""
        if not self.enabled:
            return ""
        
        prompt = f"""Generate a Python docstring for this function:

```python
{function_code[:500]}
```

Follow Google style."""

        response = self._call_llm(prompt, max_tokens=300)
        return response if response else ""
    
    def explain_complex_code(self, code: str) -> str:
        """Explain what complex code does"""
        if not self.enabled:
            return ""
        
        prompt = f"""Explain this code in simple terms (2-3 sentences):

```python
{code[:500]}
```"""

        response = self._call_llm(prompt, max_tokens=200)
        return response if response else ""
    
    def suggest_refactoring(self, code: str, filename: str) -> str:
        """Suggest refactoring opportunities"""
        if not self.enabled:
            return ""
        
        prompt = f"""Suggest refactoring improvements for this code:

```python
{code[:800]}
```

Be specific and actionable."""

        response = self._call_llm(prompt, max_tokens=400)
        return response if response else ""

