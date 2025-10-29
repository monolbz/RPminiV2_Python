#!/usr/bin/env python3
"""
Template Manager
Manages WhatsApp message templates.
"""

import json
from pathlib import Path
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TemplateManager:
    """
    Manages WhatsApp message templates.
    Templates must be pre-approved by Meta before use.
    """

    def __init__(self, templates_file=None):
        """
        Initialize template manager.

        Args:
            templates_file (str, optional): Path to templates configuration file
        """
        # Set templates file path
        if templates_file is None:
            config_dir = Path(__file__).parent.parent / 'config'
            self.templates_file = config_dir / 'templates.json'
        else:
            self.templates_file = Path(templates_file)

        # Load templates
        self.templates = self._load_templates()

    def _load_templates(self):
        """
        Load templates from configuration file.

        Returns:
            dict: Dictionary of template_name -> template_config
        """
        try:
            if self.templates_file.exists():
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    templates = json.load(f)
                    logger.info(f"Loaded {len(templates)} templates from {self.templates_file}")
                    return templates
            else:
                logger.warning(f"Templates file not found: {self.templates_file}")
                return {}
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            return {}

    def get_template(self, template_name):
        """
        Get template configuration by name.

        Args:
            template_name (str): Name of the template

        Returns:
            dict: Template configuration, or None if not found
        """
        template = self.templates.get(template_name)

        if template is None:
            logger.warning(f"Template '{template_name}' not found")
        else:
            logger.debug(f"Retrieved template '{template_name}'")

        return template

    def list_templates(self):
        """
        List all available templates.

        Returns:
            list: List of template names
        """
        return list(self.templates.keys())

    def validate_template_variables(self, template_name, variables):
        """
        Validate that the correct number of variables are provided for a template.

        Args:
            template_name (str): Name of the template
            variables (list): List of variable values

        Returns:
            tuple: (bool, str) - (is_valid, error_message)
        """
        try:
            template = self.get_template(template_name)

            if template is None:
                return False, f"Template '{template_name}' not found"

            expected_count = template.get('variables_count', 0)
            provided_count = len(variables) if variables else 0

            if provided_count != expected_count:
                return False, f"Template requires {expected_count} variables, but {provided_count} provided"

            return True, ""

        except Exception as e:
            logger.error(f"Error validating template variables: {e}")
            return False, f"Validation error: {str(e)}"

    def reload_templates(self):
        """Reload templates from file (useful for updates without restart)."""
        self.templates = self._load_templates()
        logger.info("Templates reloaded")
