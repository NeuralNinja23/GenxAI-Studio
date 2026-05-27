# app/tools/contracts.py
from pydantic import BaseModel, Field
from typing import List

class PhaseSemanticContract(BaseModel):
    phase: str
    allowed_extensions: List[str] = Field(default_factory=list)
    forbidden_patterns: List[str] = Field(default_factory=list)
    required_keywords: List[str] = Field(default_factory=list)

FRONTEND_CONTRACT = PhaseSemanticContract(
    phase="frontend_mock",
    allowed_extensions=[".tsx", ".ts", ".jsx", ".js", ".css", ".html"],
    forbidden_patterns=[
        r"spec\.[jt]sx?$",
        r"test\.[jt]sx?$",
        r"playwright",
        r"cypress"
    ],
    required_keywords=["export default", "return", "import"]
)
