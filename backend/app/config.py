"""Configuration management for V2 backend."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    SECURITY WARNING: The default values below are for development only.
    In production, ALL sensitive values MUST be set via environment variables.
    Never commit real credentials to version control.
    """

    # GitHub App (MUST be set via environment variables in production)
    github_app_id: int = 123456
    github_app_private_key: str = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4/4ggmHWI+1eUlLW8XvIHXa6L8/HiM5VzQkwj5qOkJM++7LqV0pRH+\nLVVs/ZCFK7lvjEZ3xBg7s8bvQo/R0OWdPdVWMNJCYQVYOJaL1kLRyUBR0nWvx0RL\nvE4IH3j7rKuZQm7I7VQvN/f7pNlslDTpVnpn9xYaqpO7k7g/R8kZG0NN7Udbh/+T\nW8c13l4RZfOYbVXXqX8cqS4gZ7K2bQX7hC0w7J7k0fT/f51GyJb51WRrY0oi+VPp\nYz1qVQWuqZ9w4DEGiLgPOlPj5RoQhm9T/EbvPY4W6fOUX0hKJxAbvqe8hGaSmjHL\nO8wMbrgDAgMBAAECggEAFWqIJ6S5nJ2BI4Vxx6KgxTCmvwC9F1hUCTnQ5qLaKC4p\nR0oF0l5LL8IKFa6EvvqFp9pIe4tF3yCHmD9pSRBKqGpLKH8ShwF9O6KHQE0x76Qg\nlBRo8nVP5xaEfXHmQd/pHwY5tQm9llRj9C0nfBxqczMEZRJPpgCvZWZNRLT7ZB+C\nQFJdKJOGHOgE3h3S8bMmKAYqwOV8kKLaL4VG8UH9LQrOHi4LqV8mCsZ+ByZYJLXi\na8Ys8Q5r8OPzvCJSXa4p1PJPE6B5T3HqNFO4B5rJH6fLHFNxGYeNqIf2q1iLXLSx\npUEWfNvpj7xnTvHlZK5LPPgCW9H8+0BQRUr4n7p4AQKBgQDeQdVNfSjLdNjKcaSu\nLQeQN7pB4MG4WQv7nHLmGDvtaYbmPj1KdEKzYBLJLPhFChLs0RqJ7ixBSJV5p4Wa\nGEkEBrCxnVxR0Z3TZYFnJ3TPPUBY7pBLwKOhFRvGLDd4w8pXMo1Lfqvfwk7VzKmR\nblmKGGe/5RFPFpHK1N4Q3hTlxQKBgQDcpx+gEMGO8DEfG1b1RzZZBW5lDvNgAB7T\nVEz1FZrGHqN9+jHLNM9yJDz1+5CnIrXt4BYDL/4kRhEVZJgFk0tKNvCRaKzLH9Cp\nTuHvPYJGr8B5uI0VPrPhT/oJV8blVE0UljvR5EVZX6sn5m0cQRn9yWkGCpZ8MfHT\nxUg+rI0xAQKBgG1B2j0bqL1oXh6ijQo9YBGOjGIlmBhLcWfMF0HjN7fmXdDlf5nE\nMXGYqST0j6Sx3c9fvVNxJ4oJ4o3mKJm6lPXGUx3Z6H8aKhMFYdXKT6y6B7Q9b1h5\nN+9L8EEjy9T3iLLKG8xsKOa6/MQIqTvYVwCXlxhLlGh/Ue3xLGFAqQKBgHgD0o7Z\nHrTOhY1+dBVYlmjQHGkHwVEyFKNkYG8B+D2RvG3OhCKKhEuBi0E4fJvKVRKsV1RB\nFLlHuLOMyqq/fVvJ6NjEYH+HqBVNKx5sD8j8lfHvWvWHbvMjWLF3c8mUMKEvKYl4\n2rKxDp0fE2Ye+RkRqX4iBQRnH6H8MANvVGXBAoGAPP3xhDNSKJ0MZM2xE6fTH0+P\nlKnlVp6/QJ0T1O5vwR/9Iu4C3hqE4hJDfDNjXxO2zGBuY7dXV5rZQSZ8xvMfzZ3T\nIf/xR5rL0KdSlMJpCz4nW6qHmzDLH8OqAnyGLEUDNpHR7x3jMK8wKFNvDMWB4dXH\nDx+LTuEd3yv6vKY=\n-----END PRIVATE KEY-----"
    github_client_id: str = "dev_client_id"
    github_client_secret: str = "dev_client_secret"
    github_token: Optional[str] = None  # Personal access token for PR creation

    # Database
    database_url: str = "sqlite:///./agi_engineer_v2.db"

    # Redis (for Celery background tasks)
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"

    # Security (CRITICAL: Change these in production!)
    jwt_secret_key: str = "dev-secret-key-for-local-testing"  # Min 32 chars in production
    webhook_secret: str = "dev-webhook-secret"  # Use strong random string in production

    # AI
    groq_api_key: str = ""

    # Frontend
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
