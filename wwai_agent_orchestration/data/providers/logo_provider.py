# data_providers/providers/logo_provider.py
"""
Logo Provider.

Retrieves trade-based logos from media_management database.
Logos are pre-generated per trade and matched to business via assigned trades.
"""

from wwai_agent_orchestration.core.observability.logger import get_logger
from typing import Optional, Dict, Any, List

from wwai_agent_orchestration.data.connectors.base_mongo_provider import BaseProvider
from wwai_agent_orchestration.data.providers.models.logo import (
    LogoInput,
    LogoOutput,
    LogoItem,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

DB_MEDIA = "media_management"
COLLECTION_MEDIA = "media"


# =============================================================================
# PROVIDER
# =============================================================================

class LogoProvider(BaseProvider):
    """
    Provider for trade-based logos.

    Flow:
    1. Lookup business trades from business_types collection
    2. Query media collection for media_type="logo" matching trades
    3. Return primary logo + all matching logos

    Logos are pre-generated per trade (28 trades, 1 logo each).
    """

    def get(self, input_data: LogoInput) -> LogoOutput:
        """
        Get logo(s) for a business based on assigned trades.

        Args:
            input_data: LogoInput with business_id

        Returns:
            LogoOutput with primary logo and all matching logos
        """
        business_id = input_data.business_id

        logger.info(f"Fetching logo for business_id: {business_id}")

        # =====================================================================
        # STEP 1: Get business trades
        # =====================================================================
        trades = self.get_business_trades(business_id)

        if not trades:
            logger.warning(f"No trades found for business_id: {business_id}")
            return LogoOutput(
                has_logo=False,
                primary_logo=None,
                all_logos=[],
                total_count=0,
                matched_trades=[],
            )

        logger.info(f"Business has {len(trades)} trades: {trades}")

        # =====================================================================
        # STEP 2: Query for logos matching trades
        # =====================================================================
        query = {
            "media_type": "logo",
            "trade_type": {"$in": trades}
        }

        raw_logos = self.find_many(
            DB_MEDIA,
            COLLECTION_MEDIA,
            query,
            sort=[("created_at", -1)]  # Newest first
        )

        if not raw_logos:
            logger.info(f"No logos found for trades: {trades}")
            return LogoOutput(
                has_logo=False,
                primary_logo=None,
                all_logos=[],
                total_count=0,
                matched_trades=trades,
            )

        logger.info(f"Found {len(raw_logos)} logos for trades")

        # =====================================================================
        # STEP 3: Transform to LogoItems
        # =====================================================================
        items = []
        matched_trades = set()

        for raw in raw_logos:
            item = self._transform_logo(raw)
            if item:
                items.append(item)
                matched_trades.add(item.trade_type)

        if not items:
            return LogoOutput(
                has_logo=False,
                primary_logo=None,
                all_logos=[],
                total_count=0,
                matched_trades=trades,
            )

        # Primary logo is the first one (matching first trade)
        # Try to match order of business's trades
        primary_logo = items[0]
        for trade in trades:
            for item in items:
                if item.trade_type == trade:
                    primary_logo = item
                    break
            else:
                continue
            break

        logger.info(
            f"Returning {len(items)} logos for business_id: {business_id}, "
            f"primary: {primary_logo.trade_type}"
        )

        return LogoOutput(
            has_logo=True,
            primary_logo=primary_logo,
            all_logos=items,
            total_count=len(items),
            matched_trades=list(matched_trades),
        )

    def _transform_logo(self, raw: Dict[str, Any]) -> Optional[LogoItem]:
        """Transform raw media document to LogoItem."""
        try:
            image_data = raw.get("image", {})

            url = image_data.get("src")
            if not url:
                return None

            logo_id = image_data.get("id") or str(raw.get("_id", ""))

            return LogoItem(
                logo_id=logo_id,
                url=url,
                width=image_data.get("width"),
                height=image_data.get("height"),
                aspect_ratio=image_data.get("aspect_ratio"),
                trade_type=raw.get("trade_type", ""),
                source=raw.get("source", "generated"),
            )

        except Exception as e:
            logger.error(f"Failed to transform logo: {e}")
            return None

    def get_logo_by_trade(self, trade_type: str) -> Optional[LogoItem]:
        """
        Get logo directly by trade type.

        Useful when you know the trade and don't need business lookup.

        Args:
            trade_type: Trade type string (e.g., "plumbing")

        Returns:
            LogoItem or None
        """
        raw = self.find_one(
            DB_MEDIA,
            COLLECTION_MEDIA,
            {
                "media_type": "logo",
                "trade_type": trade_type
            }
        )

        if not raw:
            return None

        return self._transform_logo(raw)

    def get_all_logos(self) -> List[LogoItem]:
        """
        Get all available logos (all trades).

        Useful for admin/debugging.

        Returns:
            List of all LogoItems
        """
        raw_logos = self.find_many(
            DB_MEDIA,
            COLLECTION_MEDIA,
            {"media_type": "logo"},
            sort=[("trade_type", 1)]  # Alphabetical by trade
        )

        items = []
        for raw in raw_logos:
            item = self._transform_logo(raw)
            if item:
                items.append(item)

        return items

    def get_logo_count(self) -> int:
        """
        Get count of all logos in database.

        Returns:
            Total logo count
        """
        try:
            collection = self.get_collection(DB_MEDIA, COLLECTION_MEDIA)
            return collection.count_documents({"media_type": "logo"})
        except Exception as e:
            logger.error(f"Failed to count logos: {e}")
            return 0
