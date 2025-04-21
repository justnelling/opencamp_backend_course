from typing import Dict, Any, Optional
from uuid import UUID

class DatabaseConnection:
    async def create_status(
        self,
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
        query = """
            INSERT INTO statuses (
                user_id, content, visibility, sensitive, spoiler_text,
                latitude, longitude, place_name, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING *
        """
        values = (
            user_id, content, visibility, sensitive, spoiler_text,
            latitude, longitude, place_name
        )
        result = await self.pool.fetchrow(query, *values)
        return dict(result) if result else None 