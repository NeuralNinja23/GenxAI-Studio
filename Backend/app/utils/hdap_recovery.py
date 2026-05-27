import ast
import re
from typing import List, Dict, Optional
from app.core.logging import log

def fingerprint_language(content: str) -> str:
    """Uses basic heuristics and AST parsing to guess the language of a code block."""
    try:
        ast.parse(content)
        return "python"
    except SyntaxError:
        pass
    
    if "import React" in content or "from 'react'" in content or "</div>" in content or "=>" in content:
        return "javascript"
        
    if "import " in content and "from " in content:
        return "typescript"
    
    return "unknown"

def infer_filename(content: str, language: str) -> Optional[str]:
    """Infers filename based on exports, classes, or imports."""
    if language == "python":
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)", content)
        if class_match:
            name = class_match.group(1).lower()
            if "router" in name:
                return f"routers/{name}.py"
            if "model" in name:
                return f"models/{name}.py"
            if "test" in name:
                return f"tests/test_{name.replace('test', '')}.py"
            return f"{name}.py"
        elif "test" in content.lower():
            return "tests/test_salvaged.py"
        else:
            return "salvaged.py"
    elif language in ["javascript", "typescript"]:
        export_match = re.search(r"export\s+default\s+(?:function\s+|class\s+)?([A-Za-z0-9_]+)", content)
        ext = "jsx" if language == "javascript" else "tsx"
        if export_match:
            name = export_match.group(1)
            if "Test" in name or "Spec" in name:
                return f"{name}.test.{ext}"
            return f"{name}.{ext}"
        elif "test(" in content or "describe(" in content:
             return f"salvaged.test.{ext}"
        else:
            return f"salvaged.{ext}"
    return None

def extract_markdown_fences(content: str) -> List[Dict[str, str]]:
    """Extracts orphan code from markdown blocks if HDAP markers are broken."""
    blocks = []
    pattern = re.compile(r"```(\w+)?\n(.*?)\n```", re.DOTALL)
    for match in pattern.finditer(content):
        lang_hint = match.group(1) or ""
        code = match.group(2).strip()
        
        language = fingerprint_language(code)
        inferred_name = infer_filename(code, language)
        
        if inferred_name:
            blocks.append({
                "path": inferred_name,
                "content": code,
                "language": language
            })
    return blocks

def recover_hdap(content: str) -> List[Dict[str, str]]:
    """
    Attempts to salvage files from a malformed HDAP response.
    Returns a list of dictionaries with 'path' and 'content'.
    """
    salvaged_files = []
    
    # Strategy 1: Malformed Marker Repair
    file_pattern = re.compile(r"<FILE\s+path=[\"']([^\"']+)[\"']\s*>(.*?)</FILE>", re.DOTALL | re.IGNORECASE)
    for match in file_pattern.finditer(content):
        path = match.group(1)
        code = match.group(2).strip()
        salvaged_files.append({"path": path, "content": code})
        
    if salvaged_files:
        log("RECOVERY", f"Salvaged {len(salvaged_files)} files via malformed marker repair.")
        return salvaged_files
        
    # Strategy 2: Markdown-Aware Extraction
    markdown_blocks = extract_markdown_fences(content)
    if markdown_blocks:
        log("RECOVERY", f"Salvaged {len(markdown_blocks)} files via markdown extraction & inference.")
        for block in markdown_blocks:
            salvaged_files.append({"path": block["path"], "content": block["content"]})
        return salvaged_files
        
    # Strategy 3: Orphan Code Salvage (Fallback)
    language = fingerprint_language(content)
    if language != "unknown":
        inferred_name = infer_filename(content, language)
        if inferred_name:
            log("RECOVERY", f"Salvaged 1 file via orphan code inference: {inferred_name}")
            salvaged_files.append({"path": inferred_name, "content": content})
            return salvaged_files
            
    return salvaged_files
