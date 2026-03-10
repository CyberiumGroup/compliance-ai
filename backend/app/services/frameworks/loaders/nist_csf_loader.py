"""Loader for NIST Cybersecurity Framework 2.0."""

import json
from pathlib import Path

from app.models.unified_framework import FrameworkType
from app.services.frameworks.loaders.base_loader import (
    BaseFrameworkLoader,
    FrameworkData,
    RequirementData,
)


class NistCsfLoader(BaseFrameworkLoader):
    """Loader for NIST Cybersecurity Framework 2.0.

    Loads the NIST CSF 2.0 framework from the csf_2_0.json data file.
    The framework has 3 hierarchy levels:
    - Level 0: Functions (GV, ID, PR, DE, RS, RC)
    - Level 1: Categories (e.g., GV.OC, ID.AM)
    - Level 2: Subcategories (e.g., GV.OC-01, ID.AM-01) - assessable
    """

    FUNCTION_ORDER = {
        "GV": 0,  # GOVERN
        "ID": 1,  # IDENTIFY
        "PR": 2,  # PROTECT
        "DE": 3,  # DETECT
        "RS": 4,  # RESPOND
        "RC": 5,  # RECOVER
    }

    def get_framework_data(self) -> FrameworkData:
        """Load NIST CSF 2.0 framework data from JSON file."""
        data = self._load_json_file()

        functions = []
        for func_data in data["functions"]:
            function = self._parse_function(func_data)
            functions.append(function)

        return FrameworkData(
            code="NIST-CSF-2.0",
            name="NIST Cybersecurity Framework",
            version="2.0",
            description=(
                "The NIST Cybersecurity Framework (CSF) 2.0 provides guidance to "
                "industry, government agencies, and other organizations to manage "
                "cybersecurity risks. It organizes cybersecurity outcomes into six "
                "Functions: Govern, Identify, Protect, Detect, Respond, and Recover."
            ),
            framework_type=FrameworkType.NIST_CSF,
            hierarchy_levels=3,
            hierarchy_labels=["Function", "Category", "Subcategory"],
            metadata={
                "release_date": data.get("framework", {}).get("release_date", "2024-02-26"),
                "official_url": "https://www.nist.gov/cyberframework",
                "total_functions": 6,
                "total_categories": 22,
                "total_subcategories": 106,
            },
            requirements=functions,
        )

    def _load_json_file(self) -> dict:
        """Load the CSF 2.0 JSON data file."""
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        file_path = data_dir / "csf_2_0.json"
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_function(self, func_data: dict) -> RequirementData:
        """Parse a CSF Function from the JSON data."""
        code = func_data["code"]
        categories = []

        for cat_idx, cat_data in enumerate(func_data["categories"]):
            category = self._parse_category(cat_data, cat_idx)
            categories.append(category)

        return RequirementData(
            code=code,
            name=func_data["name"],
            description=func_data["description"],
            level=0,
            is_assessable=False,
            display_order=self.FUNCTION_ORDER.get(code, 99),
            metadata={
                "function_type": code,
                "full_name": func_data["name"],
            },
            children=categories,
        )

    def _parse_category(self, cat_data: dict, order: int) -> RequirementData:
        """Parse a CSF Category from the JSON data."""
        subcategories = []

        for subcat_idx, subcat_data in enumerate(cat_data["subcategories"]):
            subcategory = self._parse_subcategory(subcat_data, subcat_idx)
            subcategories.append(subcategory)

        return RequirementData(
            code=cat_data["code"],
            name=cat_data["name"],
            description=cat_data["description"],
            level=1,
            is_assessable=False,
            display_order=order,
            metadata={
                "category_type": cat_data["code"].split(".")[1] if "." in cat_data["code"] else None,
            },
            children=subcategories,
        )

    def _parse_subcategory(self, subcat_data: dict, order: int) -> RequirementData:
        """Parse a CSF Subcategory from the JSON data."""
        return RequirementData(
            code=subcat_data["code"],
            name=subcat_data["code"],  # Subcategories use code as name
            description=subcat_data["description"],
            guidance=subcat_data.get("guidance"),
            level=2,
            is_assessable=True,  # Subcategories are the assessable level
            display_order=order,
            metadata={
                "implementation_examples": subcat_data.get("implementation_examples", []),
            },
        )
