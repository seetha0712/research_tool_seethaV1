"""
Render API Service for managing cloud infrastructure.
Provides start/stop/status operations for Render services.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from app.core.config import RENDER_API_KEY, RENDER_API_BASE_URL, RENDER_SERVICES

logger = logging.getLogger(__name__)

class RenderAPIError(Exception):
    """Custom exception for Render API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class RenderService:
    """Service for interacting with Render's Management API."""

    def __init__(self):
        self.api_key = RENDER_API_KEY
        self.base_url = RENDER_API_BASE_URL
        self.services = RENDER_SERVICES
        self.timeout = 30.0

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def is_configured(self) -> bool:
        """Check if Render API is properly configured."""
        return bool(self.api_key and any(
            svc.get("id") for svc in self.services.values()
        ))

    async def get_service_status(self, service_key: str) -> Dict[str, Any]:
        """
        Get the current status of a Render service.

        Args:
            service_key: Either 'database' or 'app'

        Returns:
            Dict with service status information
        """
        service_config = self.services.get(service_key)
        if not service_config or not service_config.get("id"):
            raise RenderAPIError(f"Service '{service_key}' not configured")

        service_id = service_config["id"]
        service_type = service_config.get("type", "web_service")

        # Different endpoints for different service types
        if service_type == "postgres":
            url = f"{self.base_url}/postgres/{service_id}"
        else:
            url = f"{self.base_url}/services/{service_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())

                if response.status_code == 401:
                    raise RenderAPIError("Invalid Render API key", 401)
                elif response.status_code == 404:
                    raise RenderAPIError(f"Service not found: {service_id}", 404)
                elif response.status_code != 200:
                    raise RenderAPIError(
                        f"Failed to get service status: {response.text}",
                        response.status_code
                    )

                data = response.json()
                return {
                    "service_key": service_key,
                    "service_id": service_id,
                    "name": service_config["name"],
                    "type": service_type,
                    "status": data.get("suspended", "unknown") if service_type == "postgres"
                              else data.get("suspended", "unknown"),
                    "suspended": data.get("suspended", False),
                    "raw": data
                }
        except httpx.RequestError as e:
            logger.error(f"Network error getting service status: {e}")
            raise RenderAPIError(f"Network error: {str(e)}")

    async def suspend_service(self, service_key: str) -> Dict[str, Any]:
        """
        Suspend (stop) a Render service.

        Args:
            service_key: Either 'database' or 'app'

        Returns:
            Dict with operation result
        """
        service_config = self.services.get(service_key)
        if not service_config or not service_config.get("id"):
            raise RenderAPIError(f"Service '{service_key}' not configured")

        service_id = service_config["id"]
        service_type = service_config.get("type", "web_service")

        # Different endpoints for different service types
        if service_type == "postgres":
            url = f"{self.base_url}/postgres/{service_id}/suspend"
        else:
            url = f"{self.base_url}/services/{service_id}/suspend"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self._get_headers())

                if response.status_code == 401:
                    raise RenderAPIError("Invalid Render API key", 401)
                elif response.status_code == 404:
                    raise RenderAPIError(f"Service not found: {service_id}", 404)
                elif response.status_code not in [200, 202]:
                    raise RenderAPIError(
                        f"Failed to suspend service: {response.text}",
                        response.status_code
                    )

                logger.info(f"Successfully suspended service: {service_key} ({service_id})")
                return {
                    "service_key": service_key,
                    "service_id": service_id,
                    "name": service_config["name"],
                    "action": "suspend",
                    "success": True,
                    "message": f"Service '{service_config['name']}' has been suspended"
                }
        except httpx.RequestError as e:
            logger.error(f"Network error suspending service: {e}")
            raise RenderAPIError(f"Network error: {str(e)}")

    async def resume_service(self, service_key: str) -> Dict[str, Any]:
        """
        Resume (start) a Render service.

        Args:
            service_key: Either 'database' or 'app'

        Returns:
            Dict with operation result
        """
        service_config = self.services.get(service_key)
        if not service_config or not service_config.get("id"):
            raise RenderAPIError(f"Service '{service_key}' not configured")

        service_id = service_config["id"]
        service_type = service_config.get("type", "web_service")

        # Different endpoints for different service types
        if service_type == "postgres":
            url = f"{self.base_url}/postgres/{service_id}/resume"
        else:
            url = f"{self.base_url}/services/{service_id}/resume"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self._get_headers())

                if response.status_code == 401:
                    raise RenderAPIError("Invalid Render API key", 401)
                elif response.status_code == 404:
                    raise RenderAPIError(f"Service not found: {service_id}", 404)
                elif response.status_code not in [200, 202]:
                    raise RenderAPIError(
                        f"Failed to resume service: {response.text}",
                        response.status_code
                    )

                logger.info(f"Successfully resumed service: {service_key} ({service_id})")
                return {
                    "service_key": service_key,
                    "service_id": service_id,
                    "name": service_config["name"],
                    "action": "resume",
                    "success": True,
                    "message": f"Service '{service_config['name']}' has been resumed"
                }
        except httpx.RequestError as e:
            logger.error(f"Network error resuming service: {e}")
            raise RenderAPIError(f"Network error: {str(e)}")

    async def get_all_services_status(self) -> List[Dict[str, Any]]:
        """Get status of all configured services."""
        results = []
        for service_key in self.services:
            if self.services[service_key].get("id"):
                try:
                    status = await self.get_service_status(service_key)
                    results.append(status)
                except RenderAPIError as e:
                    results.append({
                        "service_key": service_key,
                        "name": self.services[service_key]["name"],
                        "error": str(e),
                        "status": "unknown"
                    })
        return results


# Singleton instance
render_service = RenderService()
