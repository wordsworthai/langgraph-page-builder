"""
Template Management Service -- centralized template operations.

Exports:
  - template_db_service: TemplateDBService singleton
  - template_builder_service: TemplateBuilderService singleton
  - section_utils: pure data-transform utilities
"""

from wwai_agent_orchestration.utils.landing_page_builder.template.db_service import (
    template_db_service,
    TemplateDBService,
)
from wwai_agent_orchestration.utils.landing_page_builder.template.builder_service import (
    template_builder_service,
    TemplateBuilderService,
)
