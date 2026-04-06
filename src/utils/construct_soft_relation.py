from typing import TypedDict, Literal, Dict, List, Optional
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

IMPORT_RE = re.compile(r"^\s*(from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M)

class SoftRelation(TypedDict):
    source: str        
    target: str       
    type: Literal[
        "imports",
        "refers_to",
        "may_call",
        "may_use",
        "semantic_related"
    ]
    confidence: float 
    origin: str       

class SymbolInfo(TypedDict):
    symbol_id: str
    name: str
    kind: str              
    file_path: str
    description: str


def make_symbol_id(
    file_path: str,
    cls: Optional[str] = None,
    member: Optional[str] = None
) -> str:
    """
    Examples:
    - file.py::func
    - file.py::Class
    - file.py::Class.method
    - file.py::Class.attribute
    """
    if cls and member:
        return f"{file_path}::{cls}.{member}"
    if cls:
        return f"{file_path}::{cls}"
    if member:
        return f"{file_path}::{member}"
    return f"{file_path}"

def build_ssat_symbol_index(ssat: dict) -> Dict[str, SymbolInfo]:
    index: Dict[str, SymbolInfo] = {}

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            path = file["path"]

            # file symbol
            file_id = make_symbol_id(path)
            index[file_id] = {
                "symbol_id": file_id,
                "name": file["name"],
                "kind": "file",
                "file_path": path,
                "description": file.get("description", "")
            }

            # global functions
            for func in (file.get("functions") or []):
                sid = make_symbol_id(path, member=func["name"])
                index[sid] = {
                    "symbol_id": sid,
                    "name": func["name"],
                    "kind": "function",
                    "file_path": path,
                    "description": func.get("description", "")
                }

            # classes
            for cls in (file.get("classes") or []):
                cls_id = make_symbol_id(path, cls=cls["name"])
                index[cls_id] = {
                    "symbol_id": cls_id,
                    "name": cls["name"],
                    "kind": "class",
                    "file_path": path,
                    "description": cls.get("description", "")
                }

                for attr in (cls.get("attributes") or []):
                    sid = make_symbol_id(path, cls=cls["name"], member=attr["name"])
                    index[sid] = {
                        "symbol_id": sid,
                        "name": attr["name"],
                        "kind": "attribute",
                        "file_path": path,
                        "description": attr.get("description", "")
                    }

                for method in (cls.get("methods") or []):
                    sid = make_symbol_id(path, cls=cls["name"], member=method["name"])
                    index[sid] = {
                        "symbol_id": sid,
                        "name": method["name"],
                        "kind": "method",
                        "file_path": path,
                        "description": method.get("description", "")
                    }

    return index


def extract_import_relations(
    skeletons: list[dict],
    symbol_index: Dict[str, SymbolInfo]
) -> List[SoftRelation]:
    relations: List[SoftRelation] = []

    for item in skeletons:
        path = item["path"]
        code = item["skeleton_code"]

        src_file_id = make_symbol_id(path)

        for match in IMPORT_RE.finditer(code):
            mod = match.group(2) or match.group(3)
            if not mod:
                continue

            mod_path = mod.replace(".", "/") + ".py"

            tgt_file_id = make_symbol_id(mod_path)
            if tgt_file_id in symbol_index:
                relations.append({
                    "source": src_file_id,
                    "target": tgt_file_id,
                    "type": "imports",
                    "confidence": 0.9,
                    "origin": "rule_import"
                })

    return relations


def extract_symbol_reference_relations(
    skeletons: list[dict],
    symbol_index: Dict[str, SymbolInfo]
) -> List[SoftRelation]:
    relations: List[SoftRelation] = []

    name_to_symbols: Dict[str, List[str]] = {}
    for sid, info in symbol_index.items():
        name_to_symbols.setdefault(info["name"], []).append(sid)

    for item in skeletons:
        path = item["path"]
        code = item["skeleton_code"]

        src_file_id = make_symbol_id(path)

        for name, targets in name_to_symbols.items():
            if name in code:
                for tgt in targets:
                    if not tgt.startswith(path):
                        relations.append({
                            "source": src_file_id,
                            "target": tgt,
                            "type": "refers_to",
                            "confidence": 0.4,
                            "origin": "rule_symbol"
                        })

    return relations


tfidf_vectorizer = TfidfVectorizer(
    stop_words='english',  
    lowercase=True,        
    token_pattern=r'\b[a-zA-Z0-9]+\b'  
)

def semantic_score(desc_a: str, desc_b: str) -> float:
    """TF-IDF cosine similarity."""
    if not desc_a or not desc_b:
        return 0.0
    
    try:
        texts = [desc_a, desc_b]
        tfidf_matrix = tfidf_vectorizer.fit_transform(texts)
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        similarity = max(0.0, min(1.0, float(similarity)))
        return similarity
    
    except Exception as e:
        return 0.0

def extract_semantic_relations(
    symbol_index: Dict[str, SymbolInfo],
    threshold: float = 0.3
) -> List[SoftRelation]:
    relations: List[SoftRelation] = []
    symbols = list(symbol_index.values())

    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            if a["file_path"] == b["file_path"]:
                continue

            score = semantic_score(a["description"], b["description"])
            if score >= threshold:
                relations.append({
                    "source": a["symbol_id"],
                    "target": b["symbol_id"],
                    "type": "semantic_related",
                    "confidence": score,
                    "origin": "semantic"
                })

    return relations


def build_soft_relations(ssat: dict, skeletons: list[dict]) -> dict:
    symbol_index = build_ssat_symbol_index(ssat)

    relations: List[SoftRelation] = []
    relations += extract_import_relations(skeletons, symbol_index)
    relations += extract_symbol_reference_relations(skeletons, symbol_index)
    relations += extract_semantic_relations(symbol_index)

    ssat = dict(ssat)  # shallow copy
    ssat["soft_relations"] = relations

    return ssat


def flatten_ssat_symbols(ssat: dict) -> dict:
    """
    Convert the current project ssat structure into the format {path: [symbols]} and return a dict.
    Symbols include function names, class names, class methods (in the form of class.method), and class attributes (in the form of class.attribute).
    """
    flat = {}
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            path = file.get("path")
            symbols = []
            
            for func in (file.get("functions") or []):
                if "name" in func:
                    symbols.append(func["name"])
            
            for cls in (file.get("classes") or []):
                cls_name = cls.get("name")
                if cls_name:
                    symbols.append(cls_name)
                    
                    for attr in (cls.get("attributes") or []):
                        attr_name = attr.get("name")
                        if attr_name:
                            symbols.append(f"{cls_name}.{attr_name}")
                    
                    for method in (cls.get("methods") or []):
                        method_name = method.get("name")
                        if method_name:
                            symbols.append(f"{cls_name}.{method_name}")
            flat[path] = symbols
    return flat

def build_soft_relation_index(ssat: dict, skeletons: List[dict]):
    
    soft_relations = build_soft_relations(ssat, skeletons)["soft_relations"]
    outgoing = defaultdict(list)
    incoming = defaultdict(list)

    for rel in soft_relations:
        outgoing[rel["source"]].append(rel)
        incoming[rel["target"]].append(rel)

    return outgoing, incoming

def get_symbols_of_file(symbol_index: dict, file_path: str) -> list[str]:
    return symbol_index.get(file_path, []) or []


def collect_related_symbols(
    file_path: str,
    symbol_index: dict,
    outgoing_index: dict,
    incoming_index: dict,
    min_conf: float = 0.4
) -> list[str]:
    confidence_map = defaultdict(float)
    seeds = get_symbols_of_file(symbol_index, file_path)

    for sid in seeds:
        for rel in outgoing_index.get(sid, []):
            conf = rel.get("confidence", 0.0)
            if conf >= min_conf:
                tgt = rel["target"]
                confidence_map[tgt] = max(confidence_map[tgt], conf)

        for rel in incoming_index.get(sid, []):
            conf = rel.get("confidence", 0.0)
            if conf >= min_conf:
                src = rel["source"]
                confidence_map[src] = max(confidence_map[src], conf)

    sorted_symbols = sorted(
        confidence_map.keys(),
        key=lambda s: confidence_map[s],
        reverse=True
    )

    return sorted_symbols

def symbols_to_files(symbol_ids: List[str], symbol_index: dict) -> set[str]:
    return {
        symbol_index[sid]["file_path"]
        for sid in symbol_ids
        if sid in symbol_index
    }
    
def find_ssat_of_file_by_path(ssat: dict, path: str) -> dict:
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            if file.get("path") == path:
                return file
    return None

def find_skeleton_of_file_by_path(skeleton: List[dict], path: str) -> dict:
    for item in skeleton:
        if item.get("path") == path:
            return item["skeleton_code"]
    return None

def build_related_context_text(skeleton: List[dict], related_files: list[str]) -> str:
    if not related_files:
        return ""

    parts = [
        "The following files are potentially related to the target file.",
        "They are provided as reference only. Do NOT modify them.",
        ""
    ]

    for file_path in related_files:
        file_text = f"- {file_path}\n" + "```python\n" + f"{find_skeleton_of_file_by_path(skeleton, file_path)}\n" + "```"
        parts.append(file_text)
        parts.append("")

    return "\n".join(parts)


def build_context_for_init_code_generation(target_file: str, ssat: dict, skeletons: list[dict], symbol_index: dict, outgoing_index: dict, incoming_index: dict, max_files: int = 5) -> dict:
      
    related_symbols = collect_related_symbols(
        target_file,
        symbol_index,
        outgoing_index,
        incoming_index
    )

    related_files = symbols_to_files(related_symbols, symbol_index)
    related_files.discard(target_file)

    related_files = list(related_files)[:max_files]

    return {
        "target_file": {
            "ssat": find_ssat_of_file_by_path(ssat, target_file),
            "skeleton": find_skeleton_of_file_by_path(skeletons, target_file)
        },
        "related_files": [
            {
                "path": path,
                "ssat": find_ssat_of_file_by_path(ssat, path),
                "skeleton": find_skeleton_of_file_by_path(skeletons, path)
            }
            for path in related_files
        ]
    }, build_related_context_text(skeletons, related_files)
