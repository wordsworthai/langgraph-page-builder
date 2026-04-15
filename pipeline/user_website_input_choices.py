"""
User website input choices - purpose, tone, and color palette options.
"""
import random
from typing import Dict, List, Optional, TypedDict


class PurposeOption(TypedDict):
    id: str
    title: str
    description: str


class ToneOption(TypedDict):
    id: str
    title: str
    description: str


class ColorPalette(TypedDict):
    id: str
    colors: Dict[str, str]


class ColorCategory(TypedDict):
    id: str
    name: str
    description: str
    palettes: List[ColorPalette]


# Purpose options
PURPOSE_OPTIONS: List[PurposeOption] = [
    {
        "id": "lead_generation",
        "title": "Lead Generation",
        "description": "Get more inquiries, calls, and bookings from potential customers.",
    },
    {
        "id": "brand_credibility",
        "title": "Brand Credibility",
        "description": "Build trust with reviews, certifications, and a professional presence.",
    },
    {
        "id": "online_portfolio",
        "title": "Online Portfolio",
        "description": "Showcase your work, services, and past projects to win confidence.",
    },
    {
        "id": "local_discovery",
        "title": "Local Discovery",
        "description": "Help nearby customers find and contact you through search and maps.",
    },
]

# Tone options
TONE_OPTIONS: List[ToneOption] = [
    {
        "id": "professional",
        "title": "Professional",
        "description": "Clear, confident, and polished language that builds trust and credibility.",
    },
    {
        "id": "friendly",
        "title": "Friendly",
        "description": "Warm, welcoming, and conversational tone that feels approachable.",
    },
    {
        "id": "bold",
        "title": "Bold",
        "description": "Strong, energetic, and attention-grabbing statements that stand out.",
    },
    {
        "id": "minimal",
        "title": "Minimal",
        "description": "Clean, concise, and to-the-point messaging with zero fluff.",
    },
]

# Color categories with palettes
COLOR_CATEGORIES: List[ColorCategory] = [
    {
        "id": "friendly",
        "name": "Friendly",
        "description": "Warm, approachable, lively colors",
        "palettes": [
            {
                "id": "friendly-1",
                "colors": {
                    "primary": "#FF8566",
                    "secondary": "#FFD666",
                    "accent": "#B8E986",
                    "background": "#FFFEF9",
                },
            },
            {
                "id": "friendly-2",
                "colors": {
                    "primary": "#7CB8A6",
                    "secondary": "#FF9F7F",
                    "accent": "#FFD4BA",
                    "background": "#FFF8F5",
                },
            },
            {
                "id": "friendly-3",
                "colors": {
                    "primary": "#FFB5C2",
                    "secondary": "#B8A5D6",
                    "accent": "#E8DEF8",
                    "background": "#FAFAFA",
                },
            },
        ],
    },
    {
        "id": "bold",
        "name": "Bold",
        "description": "High-contrast, strong, energetic colors",
        "palettes": [
            {
                "id": "bold-1",
                "colors": {
                    "primary": "#FF0066",
                    "secondary": "#0A0A0A",
                    "accent": "#00E5FF",
                    "background": "#FFFFFF",
                },
            },
            {
                "id": "bold-2",
                "colors": {
                    "primary": "#FF6B35",
                    "secondary": "#1A0F0A",
                    "accent": "#FFB627",
                    "background": "#FFFFFF",
                },
            },
            {
                "id": "bold-3",
                "colors": {
                    "primary": "#00C2FF",
                    "secondary": "#111111",
                    "accent": "#FFB800",
                    "background": "#F5F7FA",
                },
            },
        ],
    },
    {
        "id": "minimal",
        "name": "Minimal",
        "description": "Soft, clean, modern neutrals",
        "palettes": [
            {
                "id": "minimal-1",
                "colors": {
                    "primary": "#1F1F1F",
                    "secondary": "#171717",
                    "accent": "#C6C6C6",
                    "background": "#EFEFEF",
                },
            },
            {
                "id": "minimal-2",
                "colors": {
                    "primary": "#2C3E4F",
                    "secondary": "#556B7C",
                    "accent": "#8FA5B3",
                    "background": "#F8FAFB",
                },
            },
            {
                "id": "minimal-3",
                "colors": {
                    "primary": "#3D3631",
                    "secondary": "#9B8B7E",
                    "accent": "#C4B5A0",
                    "background": "#FAF8F5",
                },
            },
        ],
    },
    {
        "id": "luxury",
        "name": "Luxury",
        "description": "Rich, elegant, premium tones",
        "palettes": [
            {
                "id": "luxury-1",
                "colors": {
                    "primary": "#C9A227",
                    "secondary": "#0F172A",
                    "accent": "#475569",
                    "background": "#FAF9F6",
                },
            },
            {
                "id": "luxury-2",
                "colors": {
                    "primary": "#2D6A4F",
                    "secondary": "#0F2922",
                    "accent": "#B8860B",
                    "background": "#F8FAF9",
                },
            },
            {
                "id": "luxury-3",
                "colors": {
                    "primary": "#6B21A8",
                    "secondary": "#1E1B4B",
                    "accent": "#C9A227",
                    "background": "#FAF7FF",
                },
            },
        ],
    },
]

# Font mapping by category
FONT_MAP: Dict[str, str] = {
    "friendly": '"Londrina Solid", sans-serif',
    "luxury": '"Limelight", sans-serif',
    "minimal": '"Public Sans", sans-serif',
    "bold": '"Oswald", sans-serif',
}

DEFAULT_FONT = '"General Sans", sans-serif'


def get_purpose_options(index: Optional[int] = None) -> PurposeOption:
    """
    Get a purpose option.
    
    Args:
        index: Optional index to select a specific purpose option.
               If provided, uses modulo to get that index from the list.
               If None, randomly samples from all purpose options.
    
    Returns:
        A single purpose option dictionary with id, title, and description.
    
    Example:
        >>> purpose = get_purpose_options(index=2)
        >>> purpose["id"]
        'online_portfolio'
        >>> purpose = get_purpose_options()  # Random sample
        >>> purpose["id"]
        'lead_generation'  # or any other random option
    """
    total_options = len(PURPOSE_OPTIONS)
    
    if index is not None:
        # Use modulo to get the index
        selected_idx = index % total_options
    else:
        # Randomly sample
        selected_idx = random.randint(0, total_options - 1)
    
    response = PURPOSE_OPTIONS[selected_idx].copy()
    return response["id"]


def get_tone_options(index: Optional[int] = None) -> ToneOption:
    """
    Get a tone option.
    
    Args:
        index: Optional index to select a specific tone option.
               If provided, uses modulo to get that index from the list.
               If None, randomly samples from all tone options.
    
    Returns:
        A single tone option dictionary with id, title, and description.
    
    Example:
        >>> tone = get_tone_options(index=1)
        >>> tone["id"]
        'friendly'
        >>> tone = get_tone_options()  # Random sample
        >>> tone["id"]
        'professional'  # or any other random option
    """
    total_options = len(TONE_OPTIONS)
    
    if index is not None:
        # Use modulo to get the index
        selected_idx = index % total_options
    else:
        # Randomly sample
        selected_idx = random.randint(0, total_options - 1)
    
    response  = TONE_OPTIONS[selected_idx].copy()
    return response["id"]


def get_all_purpose_options() -> List[PurposeOption]:
    """
    Get all available purpose options (helper function for when you need the full list).
    
    Returns:
        List of all purpose option dictionaries with id, title, and description.
    """
    return PURPOSE_OPTIONS.copy()


def get_all_tone_options() -> List[ToneOption]:
    """
    Get all available tone options (helper function for when you need the full list).
    
    Returns:
        List of all tone option dictionaries with id, title, and description.
    """
    return TONE_OPTIONS.copy()


def _expand_palettes() -> List[Dict]:
    """
    Expand all palettes from all categories into a flat list,
    each entry includes the palette data and its category.
    
    Returns:
        List of dictionaries with keys: palette, category_id, category_name
    """
    expanded = []
    for category in COLOR_CATEGORIES:
        for palette in category["palettes"]:
            expanded.append({
                "palette": palette,
                "category_id": category["id"],
                "category_name": category["name"],
            })
    return expanded


def get_expanded_palettes() -> List[Dict]:
    """
    Get all palettes expanded from all categories (public API).
    
    Returns:
        List of dicts with keys: palette, category_id, category_name.
        Use get_color_palette_and_font(index=i) for palette + font at index i.
    """
    return _expand_palettes()


def get_color_palette_and_font(index: Optional[int] = None) -> Dict:
    """
    Get a color palette and its corresponding font family.
    
    When sampling, expands all palettes from all categories as separate options.
    Uses the category to determine the appropriate font.
    
    Args:
        index: Optional index to select a specific palette.
               If provided, uses modulo to get that index from expanded list.
               If None, randomly samples from all expanded palettes.
    
    Returns:
        Dictionary with 2 keys:
            - PALETTE: Dict containing colors (primary, secondary, accent, background),
                       palette_id, and category
            - FONT_FAMILY: The font family string for this category
    
    Example:
        >>> result = get_color_palette_and_font(index=5)
        >>> result["PALETTE"]
        {'primary': '#D4AF37', 'secondary': '#1C1410', 'accent': '#8B4513',
         'background': '#FAF8F3', 'palette_id': 'luxury-1', 'category': 'luxury'}
        >>> result["FONT_FAMILY"]
        '"Limelight", sans-serif'
    """
    expanded = _expand_palettes()
    total_palettes = len(expanded)
    
    if index is not None:
        # Use modulo to get the index
        selected_idx = index % total_palettes
    else:
        # Randomly sample
        selected_idx = random.randint(0, total_palettes - 1)
    
    selected = expanded[selected_idx]
    palette = selected["palette"]
    category_id = selected["category_id"]
    
    # Get font based on category
    font_family = FONT_MAP.get(category_id, DEFAULT_FONT)
    
    # Build PALETTE dict with colors + metadata
    palette_dict = {
        **palette["colors"],  # Spread colors (primary, secondary, accent, background)
        "palette_id": palette["id"],
        "category": category_id,
    }
    
    return {
        "PALETTE": palette_dict,
        "FONT_FAMILY": font_family,
    }


def get_color_palette_and_font_by_id(palette_id: str) -> Optional[Dict]:
    """
    Get palette and font by palette ID (e.g. "friendly-1", "bold-2").

    Returns:
        Same format as get_color_palette_and_font: {PALETTE, FONT_FAMILY}, or None if not found.
    """
    expanded = _expand_palettes()
    for item in expanded:
        if item["palette"]["id"] == palette_id:
            palette = item["palette"]
            category_id = item["category_id"]
            font_family = FONT_MAP.get(category_id, DEFAULT_FONT)
            palette_dict = {
                **palette["colors"],
                "palette_id": palette["id"],
                "category": category_id,
            }
            return {"PALETTE": palette_dict, "FONT_FAMILY": font_family}
    return None


def get_category_from_palette_id(palette_id: str) -> Optional[str]:
    """
    Get the category ID for a given palette ID.
    
    Args:
        palette_id: The palette ID (e.g., "friendly-1", "bold-2")
    
    Returns:
        The category ID (e.g., "friendly", "bold") or None if not found.
    """
    for category in COLOR_CATEGORIES:
        if any(p["id"] == palette_id for p in category["palettes"]):
            return category["id"]
    return None


def get_font_family_from_category(category_id: Optional[str]) -> str:
    """
    Map category ID to font family.
    
    Args:
        category_id: The category ID (friendly, bold, minimal, luxury) or None
    
    Returns:
        The font family string for the category, or default font if not found.
    """
    if category_id:
        return FONT_MAP.get(category_id, DEFAULT_FONT)
    return DEFAULT_FONT
