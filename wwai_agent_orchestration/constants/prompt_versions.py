"""
Single source of truth for all prompt names and versions.
Used by PromptSpec classes (autopop), LLMConfig, and workflow nodes.
Prompt names map to .txt filenames under prompts/. Changing the constant here overrides which file is loaded.
"""

# --- Data Preparation ---
TRADE_CLASSIFICATION_PROMPT_NAME = "landing_page_builder/data_preparation/trade_classification"
TRADE_CLASSIFICATION_PROMPT_VERSION = "1"

# --- Campaign Intent ---
CAMPAIGN_QUERY_SYNTHESIS_PROMPT_NAME = "landing_page_builder/campaign_intent/campaign_query_synthesis"
CAMPAIGN_QUERY_SYNTHESIS_PROMPT_VERSION = "3"

SCREENSHOT_INTENT_EXTRACTION_PROMPT_NAME = "landing_page_builder/campaign_intent/dummy_campaign_intent_generation"
SCREENSHOT_INTENT_EXTRACTION_PROMPT_VERSION = None

# --- Template Selection ---
TEMPLATE_SECTION_STRUCTURE_GENERATION_PROMPT_NAME = "landing_page_builder/template_selection/template_section_structure_generation"
TEMPLATE_SECTION_STRUCTURE_GENERATION_PROMPT_VERSION = "3"

RESOLVE_TEMPLATE_SECTIONS_PROMPT_NAME = "landing_page_builder/template_selection/resolve_template_sections"
RESOLVE_TEMPLATE_SECTIONS_PROMPT_VERSION = "1"

TEMPLATE_EVALUATION_PROMPT_NAME = "landing_page_builder/template_selection/template_evaluation"
TEMPLATE_EVALUATION_PROMPT_VERSION = "5"

# --- URL Context ---
GEMINI_URL_CONTEXT_PROMPT_NAME = "landing_page_builder/url_context/gemini_url_context_extraction"
GEMINI_URL_CONTEXT_PROMPT_VERSION = None

# --- Autopop ---
BUTTON_COLOR_AUTOPOP_PROMPT_NAME = "landing_page_builder/autopop/button_color_autopop"
BUTTON_COLOR_AUTOPOP_PROMPT_VERSION = 3

TEXT_COLOR_AUTOPOP_PROMPT_NAME = "landing_page_builder/autopop/text_color_autopop"
TEXT_COLOR_AUTOPOP_PROMPT_VERSION = 6

BACKGROUND_COLOR_AUTOPOP_PROMPT_NAME = "landing_page_builder/autopop/background_color_autopopulation"
BACKGROUND_COLOR_AUTOPOP_PROMPT_VERSION = 1

SEMANTIC_NAME_MAPPING_PROMPT_NAME = "landing_page_builder/autopop/semantic_name_mapping"
SEMANTIC_NAME_MAPPING_PROMPT_VERSION = 3

MISC_COLOR_AUTOPOP_PROMPT_NAME = "landing_page_builder/autopop/misc_color_autopop"
MISC_COLOR_AUTOPOP_PROMPT_VERSION = 2

CONTENT_AGENT_PROMPT_NAME = "landing_page_builder/autopop/content_agent_prompt"
CONTENT_AGENT_PROMPT_VERSION = 10

# Legacy aliases (for backward compatibility during migration)
CAMPAIGN_INTENT_PROMPT_VERSION = CAMPAIGN_QUERY_SYNTHESIS_PROMPT_VERSION
TEMPLATE_L0_L1_PROMPT_VERSION = TEMPLATE_SECTION_STRUCTURE_GENERATION_PROMPT_VERSION
SECTION_MAPPING_PROMPT_VERSION = RESOLVE_TEMPLATE_SECTIONS_PROMPT_VERSION
EVALUATION_PROMPT_VERSION = TEMPLATE_EVALUATION_PROMPT_VERSION
