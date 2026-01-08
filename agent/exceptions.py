"""
Custom exceptions for AGI Engineer
"""

class AGIEngineerError(Exception):
    """Base exception for all AGI Engineer errors"""
    pass

class RepositoryError(AGIEngineerError):
    """Errors related to repository operations"""
    pass

class AnalysisError(AGIEngineerError):
    """Errors during code analysis"""
    pass

class FixerError(AGIEngineerError):
    """Errors during fix application"""
    pass

class AIError(AGIEngineerError):
    """Errors related to AI provider calls"""
    pass

class ConfigurationError(AGIEngineerError):
    """Errors in configuration"""
    pass

class RateLimitError(AGIEngineerError):
    """Rate limit exceeded"""
    pass
