from typing import Dict, Any, Optional
from uuid import UUID
from project.database.connection import get_connection

class StatusModel:
    @staticmethod
    async def create_status(
        user_id: UUID,
        content: str,
        visibility: str = "public",
        sensitive: bool = False,
        spoiler_text: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        place_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new status."""
        async with get_connection() as conn:
            result = await conn.create_status(
                user_id=user_id,
                content=content,
                visibility=visibility,
                sensitive=sensitive,
                spoiler_text=spoiler_text,
                latitude=latitude,
                longitude=longitude,
                place_name=place_name
            )
            return result 