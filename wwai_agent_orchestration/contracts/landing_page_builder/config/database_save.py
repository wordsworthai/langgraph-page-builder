"""
Database save configuration for Landing Page Builder Workflow.
"""

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseSaveConfig:
    """MongoDB save behavior for template and section-mapped recommendations."""

    enable_database_save: bool = True
    save_database_name: str = "template_generation"
    save_password_secret: str = field(default_factory=lambda: os.environ.get("MONGO_PASSWORD_SECRET", ""))
    save_ip_secret: str = field(default_factory=lambda: os.environ.get("MONGO_IP_SECRET", ""))
    save_username: str = field(default_factory=lambda: os.environ.get("MONGO_USERNAME", ""))
    template_collection: str = "template_layout_recommendation"
    section_mapped_collection: str = "template_section_mapped_layout_recommendation"
    save_template_recommendation: bool = True
    save_resolved_template_recommendations: bool = True
    fail_on_save_error: bool = True
