from typing import Any, Dict, List, Optional

from wwai_agent_orchestration.data.providers.section_catalog_provider import SectionCatalogProvider
from wwai_agent_orchestration.data.providers.trades_catalog_provider import TradesCatalogProvider
from wwai_agent_orchestration.data.providers.trade_classification_provider import TradeClassificationProvider

from data_providers.utils import require_arg


def run_trades_catalog(args: Dict[str, Any], allow_external: bool) -> List[Dict[str, str]]:
    del allow_external
    return TradesCatalogProvider().fetch_trades(
        database_name=args.get("database_name"),
        collection_name=args.get("collection_name"),
        query_filter=args.get("query_filter"),
        projection=args.get("projection"),
    )


def run_trade_classification(args: Dict[str, Any], allow_external: bool) -> Optional[Dict[str, Any]]:
    del allow_external
    return TradeClassificationProvider().get_by_business_id(require_arg(args, "business_id"))


def run_section_fetch_all(args: Dict[str, Any], allow_external: bool) -> List[Dict[str, Any]]:
    del allow_external
    return SectionCatalogProvider().fetch_sections_with_metadata(
        query_filter=args.get("query_filter"),
    )


def run_section_l0_categories(args: Dict[str, Any], allow_external: bool) -> List[Dict[str, Any]]:
    del allow_external
    return SectionCatalogProvider().get_unique_l0_categories(
        query_filter=args.get("query_filter"),
    )


def run_section_by_l0(args: Dict[str, Any], allow_external: bool) -> List[Dict[str, Any]]:
    del allow_external
    return SectionCatalogProvider().get_sections_by_l0(
        l0_category=require_arg(args, "l0_category"),
        query_filter=args.get("query_filter"),
    )

