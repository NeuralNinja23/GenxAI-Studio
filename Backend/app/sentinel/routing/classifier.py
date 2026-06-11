# app/sentinel/routing/classifier.py
from typing import List, Set, Dict, Any, Optional
from pydantic import BaseModel, Field
from .failure_taxonomy import (
    FailureDomain,
    FailureCategory,
    CATEGORY_DOMAIN_MAP,
    CATEGORY_PRIORITY,
)

class FailureProfile(BaseModel):
    primary: FailureDomain = FailureDomain.UNKNOWN
    secondary: Set[FailureDomain] = Field(default_factory=set)
    domain_counts: Dict[str, int] = Field(default_factory=dict)
    severity_score: float = 0.0
    primary_category: FailureCategory = FailureCategory.UNKNOWN
    active_categories: List[FailureCategory] = Field(default_factory=list)

class FailureClassifier:
    @staticmethod
    def classify(failures: List[Any]) -> FailureProfile:
        if not failures:
            return FailureProfile(
                primary=FailureDomain.UNKNOWN,
                secondary=set(),
                domain_counts={},
                severity_score=0.0,
                primary_category=FailureCategory.UNKNOWN,
                active_categories=[]
            )

        active_categories_set = set()
        resolved_categories = []

        for f in failures:
            # Get category from fingerprint
            cat = getattr(f, "category", None)
            if cat is None:
                # Apply fallback heuristic mapping
                failure_type = getattr(f, "failure_type", "") or ""
                stage = getattr(f, "stage", "") or ""

                if (
                    "INFRASTRUCTURE" in failure_type
                    or "DOCKER" in failure_type
                    or "CONTAINER" in failure_type
                    or failure_type in ("COMPILER_UNAVAILABLE", "PACKAGE_JSON_MISSING")
                ):
                    cat = FailureCategory.INFRASTRUCTURE_FAILURE
                elif failure_type == "PROJECTOR_FAILURE":
                    cat = FailureCategory.PROJECTOR_FAILURE
                elif (
                    failure_type.startswith("TS")
                    or failure_type in ("BACKEND_BUILD_FAILURE", "FRONTEND_BUILD_FAILURE")
                    or failure_type.startswith("COMPILER_")
                    or "TS" in failure_type
                ):
                    cat = FailureCategory.COMPILER_FAILURE
                elif failure_type in (
                    "STATE_BINDING_FAILURE",
                    "RUNTIME_STATE_FAILURE",
                    "RUNTIME_BOOT_FAILURE",
                    "ORPHANED_STATE_MUTATION",
                    "STATE_MUTATION_MISSING",
                    "INVALID_STATE_TARGET",
                    "UNRESOLVED_EVENT_HANDLER",
                    "HEALTH_CHECK_FAILURE",
                    "VISUAL_RENDER_FAILURE",
                ):
                    cat = FailureCategory.RUNTIME_STATE_FAILURE
                elif failure_type in (
                    "TOPOLOGY_INTEGRITY_FAILURE",
                    "UNRESOLVED_IMPORT_FAILURE",
                    "ARTIFACT_DEPENDENCY_FAILURE",
                    "ENTRY_ROUTE_FAILURE",
                ):
                    cat = FailureCategory.GRAPH_STATE_FAILURE
                else:
                    cat = FailureCategory.UNKNOWN

            resolved_categories.append(cat)
            active_categories_set.add(cat)

        # active_categories = sorted list of active category values (represented as FailureCategory enums)
        # We sort alphabetically or by priority? Let's sort alphabetically for standard sorted set, or by priority.
        # The plan says "sorted set of category values". Let's do sorted list of category values.
        active_categories = sorted(list(active_categories_set), key=lambda x: x.value)

        # primary_category = first category in CATEGORY_PRIORITY that's in active_categories
        primary_category = FailureCategory.UNKNOWN
        for priority_cat in CATEGORY_PRIORITY:
            if priority_cat in active_categories_set:
                primary_category = priority_cat
                break
        if primary_category == FailureCategory.UNKNOWN and active_categories_set:
            # Fallback if active_categories_set only contains UNKNOWN
            primary_category = FailureCategory.UNKNOWN

        # primary domain = CATEGORY_DOMAIN_MAP[primary_category]
        primary_domain = CATEGORY_DOMAIN_MAP.get(primary_category, FailureDomain.UNKNOWN)

        # domain_counts = {domain_name: count} from mapping all failures' resolved categories via CATEGORY_DOMAIN_MAP
        domain_counts = {}
        for cat in resolved_categories:
            domain = CATEGORY_DOMAIN_MAP.get(cat, FailureDomain.UNKNOWN)
            domain_counts[domain.value] = domain_counts.get(domain.value, 0) + 1

        # secondary = set of all other domains that have count > 0 (excluding the primary domain)
        secondary_domains = set()
        for dom_val, count in domain_counts.items():
            if count > 0:
                dom = FailureDomain(dom_val)
                if dom != primary_domain:
                    secondary_domains.add(dom)

        severity_score = float(len(active_categories_set))

        return FailureProfile(
            primary=primary_domain,
            secondary=secondary_domains,
            domain_counts=domain_counts,
            severity_score=severity_score,
            primary_category=primary_category,
            active_categories=active_categories
        )
