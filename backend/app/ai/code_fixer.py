"""AI-powered code fix generation using Groq or Claude."""

from abc import ABC, abstractmethod
from typing import Optional
import os


class AIProvider(ABC):
    """Base class for AI providers."""
    
    @abstractmethod
    async def generate_fix(self, issue: dict, code_snippet: str) -> str:
        """Generate a fix suggestion for a code issue.
        
        Args:
            issue: Issue details {rule_id, name, message, category, severity}
            code_snippet: The problematic code
            
        Returns:
            Fixed code as string
        """
        pass

    @abstractmethod
    async def generate_explanation(self, issue: dict, fix: str) -> str:
        """Generate explanation for the fix.
        
        Args:
            issue: Issue details
            fix: Generated fix code
            
        Returns:
            Explanation text
        """
        pass


class GroqProvider(AIProvider):
    """Groq API provider for code fixes (free tier available)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError("Groq package not installed. Run: pip install groq")

    async def generate_fix(self, issue: dict, code_snippet: str) -> str:
        """Generate fix using Groq LLM."""
        prompt = f"""You are an expert code reviewer. Fix the following code issue:

Issue: {issue.get('name')}
Category: {issue.get('category')}
Severity: {issue.get('severity')}
Message: {issue.get('message')}

Original Code:
```
{code_snippet}
```

Provide ONLY the fixed code without explanations. Use the same language and style."""

        try:
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",  # Free tier model
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temp for consistent fixes
                max_tokens=1024,
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

    async def generate_explanation(self, issue: dict, fix: str) -> str:
        """Generate explanation using Groq."""
        prompt = f"""Explain briefly why this fix resolves the issue:

Issue: {issue.get('name')}
Problem: {issue.get('message')}

Fixed Code:
```
{fix}
```

Provide a concise explanation (1-2 sentences)."""

        try:
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=256,
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")


class ClaudeProvider(AIProvider):
    """Claude API provider for code fixes (paid)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

    async def generate_fix(self, issue: dict, code_snippet: str) -> str:
        """Generate fix using Claude."""
        prompt = f"""You are an expert code reviewer. Fix the following code issue:

Issue: {issue.get('name')}
Category: {issue.get('category')}
Severity: {issue.get('severity')}
Message: {issue.get('message')}

Original Code:
```
{code_snippet}
```

Provide ONLY the fixed code without explanations. Use the same language and style."""

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fastest/cheapest model
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    async def generate_explanation(self, issue: dict, fix: str) -> str:
        """Generate explanation using Claude."""
        prompt = f"""Explain briefly why this fix resolves the issue:

Issue: {issue.get('name')}
Problem: {issue.get('message')}

Fixed Code:
```
{fix}
```

Provide a concise explanation (1-2 sentences)."""

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")


def get_ai_provider(provider: str = "groq") -> AIProvider:
    """Factory function to get AI provider.
    
    Args:
        provider: "groq" or "claude"
        
    Returns:
        AI provider instance
    """
    if provider.lower() == "groq":
        return GroqProvider()
    elif provider.lower() == "claude":
        return ClaudeProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}")
