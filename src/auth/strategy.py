"""Auth header strategy abstraction for easy switching between header types."""

from abc import ABC, abstractmethod


class AuthHeaderStrategy(ABC):
    """Abstract base class for auth header strategies."""

    @abstractmethod
    def get_header_name(self) -> str:
        """Return the header name for authentication."""
        pass

    @abstractmethod
    def format_header_value(self, token: str) -> str:
        """Format the token value for the header."""
        pass

    def get_auth_header(self, token: str) -> dict[str, str]:
        """Return complete auth header dict."""
        return {self.get_header_name(): self.format_header_value(token)}


class AccessTokenStrategy(AuthHeaderStrategy):
    """Strategy for Access-Token header (non-standard)."""

    def get_header_name(self) -> str:
        return "Access-Token"

    def format_header_value(self, token: str) -> str:
        return token


class BearerTokenStrategy(AuthHeaderStrategy):
    """Strategy for standard Authorization: Bearer header."""

    def get_header_name(self) -> str:
        return "Authorization"

    def format_header_value(self, token: str) -> str:
        return f"Bearer {token}"


def get_auth_strategy(strategy_type: str = "access-token") -> AuthHeaderStrategy:
    """Factory function to get the appropriate auth strategy.

    Args:
        strategy_type: Either "access-token" or "bearer"

    Returns:
        AuthHeaderStrategy implementation
    """
    strategies: dict[str, type[AuthHeaderStrategy]] = {
        "access-token": AccessTokenStrategy,
        "bearer": BearerTokenStrategy,
    }

    strategy_class = strategies.get(strategy_type.lower())
    if strategy_class is None:
        raise ValueError(f"Unknown auth strategy: {strategy_type}")

    return strategy_class()
