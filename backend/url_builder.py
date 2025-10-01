"""
URL Builder Utility

Centralized URL construction for all backend services.
Eliminates hardcoded URLs and ensures consistency.
"""

import os
from urllib.parse import urljoin


class URLBuilder:
    """Build URLs for backend services"""

    def __init__(self):
        # Get base URLs from environment with sensible defaults
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8082")
        self.pi_host = os.getenv("PI_HOST", "helios.local")
        self.pi_port = int(os.getenv("PI_PORT", "8080"))

        # Ensure backend URL doesn't have trailing slash
        self.backend_url = self.backend_url.rstrip("/")

    @property
    def pi_base_url(self) -> str:
        """Get Pi base URL"""
        return f"http://{self.pi_host}:{self.pi_port}"

    def backend(self, path: str = "") -> str:
        """
        Build backend URL.

        Args:
            path: Path to append (e.g., "/images/profile-a/capture_123.jpg")

        Returns:
            Full backend URL
        """
        if not path:
            return self.backend_url

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        return f"{self.backend_url}{path}"

    def pi(self, path: str = "") -> str:
        """
        Build Pi URL.

        Args:
            path: Path to append (e.g., "/latest-image?profile=a")

        Returns:
            Full Pi URL
        """
        if not path:
            return self.pi_base_url

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        return f"{self.pi_base_url}{path}"

    def image(self, profile: str, filename: str, source: str = "backend") -> str:
        """
        Build image URL.

        Args:
            profile: Profile letter (a-f)
            filename: Image filename
            source: "backend" or "pi"

        Returns:
            Full image URL
        """
        if source == "backend":
            return self.backend(f"/images/profile-{profile}/{filename}")
        else:
            return self.pi(f"/images/profile-{profile}/{filename}")


# Singleton instance
_url_builder = None


def get_url_builder() -> URLBuilder:
    """Get singleton URLBuilder instance"""
    global _url_builder
    if _url_builder is None:
        _url_builder = URLBuilder()
    return _url_builder
