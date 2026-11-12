"""
User-Configurable Business Rules & Domain Path Matching Service.

Allows engineering leads to define path-pattern rules per workspace:
e.g.
  - "services/payment/**" -> criticality=95.0, customer_impact=95.0, domain="payment"
  - "auth/**"             -> criticality=94.0, customer_impact=90.0, domain="auth"
  - "scripts/**"          -> criticality=20.0, customer_impact=15.0, domain="tooling"
  - "tests/**"            -> criticality=15.0, customer_impact=10.0, domain="testing"

Applies matched rules to BusinessContext and triggers priority recalculation.
"""

import fnmatch
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.models import SourceFile, BusinessContext
from backend.services.priority_service import PriorityService
from backend.services.recommendation_service import RecommendationService

DEFAULT_WORKSPACE_RULES: List[Dict[str, Any]] = [
    {
        "pattern": "*payment*/**",
        "business_criticality": 95.0,
        "customer_impact": 95.0,
        "module_criticality": 90.0,
        "domain_tag": "payment",
    },
    {
        "pattern": "*auth*/**",
        "business_criticality": 92.0,
        "customer_impact": 90.0,
        "module_criticality": 92.0,
        "domain_tag": "auth",
    },
    {
        "pattern": "*order*/**",
        "business_criticality": 88.0,
        "customer_impact": 85.0,
        "module_criticality": 85.0,
        "domain_tag": "orders",
    },
    {
        "pattern": "*script*/**",
        "business_criticality": 25.0,
        "customer_impact": 15.0,
        "module_criticality": 20.0,
        "domain_tag": "tooling",
    },
    {
        "pattern": "*test*/**",
        "business_criticality": 20.0,
        "customer_impact": 10.0,
        "module_criticality": 15.0,
        "domain_tag": "testing",
    },
]


class BusinessRulesEngine:
    @staticmethod
    def match_path_rule(file_path: str, custom_rules: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Finds the first matching rule for a given file path."""
        norm_path = file_path.replace("\\", "/").lower()
        rules = (custom_rules or []) + DEFAULT_WORKSPACE_RULES

        for rule in rules:
            pattern = rule["pattern"].lower()
            if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(norm_path, f"*{pattern}*"):
                return rule
        return None

    @classmethod
    def apply_rules_to_repository(
        cls,
        db: Session,
        repository_id: int,
        custom_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Evaluates path rules against all source files in a repository.
        Updates matching BusinessContext entries and recalculates priority.
        Returns the number of files updated.
        """
        files = db.query(SourceFile).filter(
            SourceFile.repository_id == repository_id,
            SourceFile.is_active == True,
        ).all()

        updated_count = 0
        for f in files:
            matched_rule = cls.match_path_rule(f.file_path, custom_rules)
            if matched_rule:
                bctx = f.business_context
                if not bctx:
                    bctx = BusinessContext(
                        workspace_id=f.workspace_id,
                        file_id=f.id,
                        business_criticality=matched_rule.get("business_criticality", 60.0),
                        customer_impact=matched_rule.get("customer_impact", 50.0),
                        module_criticality=matched_rule.get("module_criticality", 50.0),
                        release_proximity=75.0,
                        sprint_urgency=70.0,
                        domain_tag=matched_rule.get("domain_tag", "core"),
                        provenance="USER_RULE",
                    )
                    db.add(bctx)
                else:
                    bctx.business_criticality = matched_rule.get("business_criticality", bctx.business_criticality)
                    bctx.customer_impact = matched_rule.get("customer_impact", bctx.customer_impact)
                    bctx.module_criticality = matched_rule.get("module_criticality", bctx.module_criticality)
                    bctx.domain_tag = matched_rule.get("domain_tag", bctx.domain_tag)
                    bctx.provenance = "USER_RULE"

                db.commit()
                PriorityService.calculate_file_priority(db, f.id)
                RecommendationService.generate_file_recommendation(db, f.id)
                updated_count += 1

        return updated_count
