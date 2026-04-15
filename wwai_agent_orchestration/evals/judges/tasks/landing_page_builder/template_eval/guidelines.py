"""Guidelines for template evaluation by website intent."""

from typing import Any, Dict, List


INTENT_GUIDELINES: Dict[str, Dict[str, Any]] = {
    "lead_generation": {
        "display_name": "Lead Generation",
        "required": [
            {"l0": "Hero", "l1_options": ["Text with Form", "Text Overlay"], "reason": "Must capture attention + have CTA"},
            {"l0": "Contact", "l1_options": ["Contact Form"], "reason": "Primary conversion mechanism"},
        ],
        "recommended": [
            {"l0": "Social Proof", "l1_options": ["Review Carousel", "Review Grid"], "reason": "Builds trust before form fill"},
            {"l0": "Services", "l1_options": ["Benefits List", "Feature Cards"], "reason": "Clarifies value proposition"},
            {"l0": "FAQ", "l1_options": ["FAQ"], "reason": "Handles objections pre-conversion"},
        ],
        "anti_patterns": [
            {"check": "no_form_present", "description": "No form present anywhere on page", "severity": "critical"},
            {"check": "hero_without_cta", "description": "Hero without CTA", "severity": "high"},
            {"check": "too_many_ctas", "description": "More than 2 CTAs competing (confusing)", "severity": "medium"},
            {"check": "gallery_distraction", "description": "Gallery/Portfolio sections (distraction for lead gen)", "severity": "medium"},
            {"check": "navbar_too_many_links", "description": "Navigation Bar with too many links (exit paths)", "severity": "low"},
        ],
    },
    "brand_credibility": {
        "display_name": "Brand Credibility",
        "required": [
            {"l0": "Hero", "l1_options": ["Any"], "reason": "Establishes professional presence"},
            {"l0": "Content", "l1_options": ["Text and Image", "Text Only"], "reason": "Story/mission/about"},
            {"l0": "Social Proof", "l1_options": ["Any"], "reason": "External validation"},
        ],
        "recommended": [
            {"l0": "Gallery", "l1_options": ["Portfolio Grid"], "reason": "Shows real work/results"},
            {"l0": "Banner", "l1_options": ["Text with Video"], "reason": "Video humanizes brand"},
            {"l0": "Social Proof", "l1_options": ["Press Mention"], "reason": "Third-party credibility"},
        ],
        "anti_patterns": [
            {"check": "no_social_proof", "description": "No Social Proof section at all", "severity": "critical"},
            {"check": "no_about_content", "description": "No 'about/story' Content section", "severity": "high"},
            {"check": "heavy_form_focus", "description": "Heavy form focus (feels salesy, not credible)", "severity": "medium"},
            {"check": "missing_footer", "description": "Missing Footer (looks unprofessional)", "severity": "medium"},
        ],
    },
    "online_portfolio": {
        "display_name": "Online Portfolio",
        "required": [
            {"l0": "Hero", "l1_options": ["Text Overlay", "Text and Image"], "reason": "Introduction/positioning"},
            {"l0": "Gallery", "l1_options": ["Portfolio Grid", "Editorial Grid"], "reason": "Core purpose of the page"},
            {"l0": "Contact", "l1_options": ["Contact Form", "Location Map"], "reason": "How to hire/reach"},
        ],
        "recommended": [
            {"l0": "Services", "l1_options": ["Service Grid", "Feature Cards"], "reason": "What you offer"},
            {"l0": "Content", "l1_options": ["Text and Image"], "reason": "About/bio section"},
            {"l0": "Social Proof", "l1_options": ["Review Carousel", "Testimonial Grid"], "reason": "Client validation"},
        ],
        "anti_patterns": [
            {"check": "no_gallery", "description": "No Gallery section (defeats purpose)", "severity": "critical"},
            {"check": "sparse_gallery", "description": "Gallery with < 3 items (looks sparse)", "severity": "high"},
            {"check": "missing_contact", "description": "Missing Contact info", "severity": "high"},
            {"check": "no_services_clarity", "description": "No Services/offerings clarity", "severity": "medium"},
        ],
    },
    "local_discovery": {
        "display_name": "Local Discovery",
        "required": [
            {"l0": "Hero", "l1_options": ["Any"], "reason": "First impression"},
            {"l0": "Contact", "l1_options": ["Location Map"], "reason": "Critical for local intent"},
            {"l0": "Contact", "l1_options": ["Contact Form"], "reason": "Conversion path (or click-to-call)"},
        ],
        "recommended": [
            {"l0": "Social Proof", "l1_options": ["Review Carousel", "Review Grid"], "reason": "Local SEO + trust"},
            {"l0": "Services", "l1_options": ["Service Grid", "Benefits List"], "reason": "What you offer + pricing hints"},
            {"l0": "Gallery", "l1_options": ["Portfolio Grid"], "reason": "Show the physical location/work"},
            {"l0": "FAQ", "l1_options": ["FAQ"], "reason": "Hours, parking, common questions"},
        ],
        "anti_patterns": [
            {"check": "no_location_map", "description": "No Location Map (critical miss)", "severity": "critical"},
            {"check": "no_phone_address", "description": "No phone/address visible", "severity": "high"},
            {"check": "no_reviews", "description": "No reviews (huge for local)", "severity": "high"},
            {"check": "missing_navbar", "description": "Missing Navigation Bar (mobile users need quick access)", "severity": "medium"},
            {"check": "missing_footer_nap", "description": "Missing Footer with NAP (Name, Address, Phone)", "severity": "medium"},
        ],
    },
}


def get_guidelines_for_intent(intent: str) -> Dict[str, Any]:
    if intent not in INTENT_GUIDELINES:
        raise ValueError(f"Unknown intent: {intent}. Available: {list(INTENT_GUIDELINES.keys())}")
    return INTENT_GUIDELINES[intent]


def format_guidelines_for_prompt(intent: str) -> str:
    guidelines = get_guidelines_for_intent(intent)
    lines = [f"Guidelines for {guidelines['display_name']}:", ""]
    lines.append("REQUIRED SECTIONS (page incomplete without these):")
    for req in guidelines["required"]:
        lines.append(f"  - L0: {req['l0']}, L1 options: [{', '.join(req['l1_options'])}]")
        lines.append(f"    Reason: {req['reason']}")
    lines.append("")
    lines.append("STRONGLY RECOMMENDED:")
    for rec in guidelines["recommended"]:
        lines.append(f"  - L0: {rec['l0']}, L1 options: [{', '.join(rec['l1_options'])}]")
        lines.append(f"    Reason: {rec['reason']}")
    lines.append("")
    lines.append("ANTI-PATTERNS TO FLAG:")
    for anti in guidelines["anti_patterns"]:
        lines.append(f"  - [{anti['severity'].upper()}] {anti['description']}")
    return "\n".join(lines)

