import ast
from typing import Set, Tuple, Dict, Optional

class ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)

class CallAndClassCollector(ast.NodeVisitor):
    def __init__(self):
        self.calls = set()
        self.used_classes = set()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
            self.used_classes.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)


def build_ssat_symbol_index(ssat: dict) -> dict:
    """
    symbol_name -> SSAT node (function / method / class)
    """
    index = {}

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            for fn in file.get("functions", []) or []:
                index[fn["name"]] = fn

            for cls in (file.get("classes") or []) or []:
                index[cls["name"]] = cls
                for m in cls.get("methods", []) or []:
                    index[m["name"]] = m

    return index

def analyze_function_body(func_node: ast.AST) -> dict:
    collector = CallAndClassCollector()
    collector.visit(func_node)

    return {
        "calls": list(collector.calls),
        "uses_classes": list(collector.used_classes),
    }

def enrich_file_relations(file_ssat: dict, imports: set):
    file_ssat.setdefault("realized_relations", {})
    file_ssat["realized_relations"]["imports"] = sorted(imports)

def enrich_function_relations(
    func_ssat: dict,
    analysis: dict,
    symbol_index: dict
):
    resolved_calls = []
    resolved_classes = []

    for name in analysis.get("calls", []):
        if name in symbol_index:
            resolved_calls.append(name)

    for name in analysis.get("uses_classes", []):
        if name in symbol_index:
            resolved_classes.append(name)

    func_ssat.setdefault("realized_relations", {})
    func_ssat["realized_relations"]["calls"] = resolved_calls
    func_ssat["realized_relations"]["uses_classes"] = resolved_classes

def realize_ssat_relations(
    ssat: dict,
    init_code: list[dict]
) -> dict:
    """
    Use generated code to ground SSAT soft relations.
    """
    symbol_index = build_ssat_symbol_index(ssat)

    # path -> SSAT file node
    file_index = {}
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            file_index[file["path"]] = file

    for file_item in init_code:
        path = file_item["path"]
        code = file_item["code"]

        if path not in file_index:
            continue

        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue

        file_ssat = file_index[path]

        # -------- file-level imports --------
        import_collector = ImportCollector()
        import_collector.visit(tree)
        enrich_file_relations(file_ssat, import_collector.imports)

        # -------- function / method-level --------
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name in symbol_index:
                    analysis = analyze_function_body(node)
                    enrich_function_relations(
                        symbol_index[node.name],
                        analysis,
                        symbol_index
                    )

            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name in symbol_index:
                            analysis = analyze_function_body(item)
                            enrich_function_relations(
                                symbol_index[item.name],
                                analysis,
                                symbol_index
                            )

    return ssat

def build_symbol_to_file_index(ssat: dict) -> dict:
    """
    symbol_name -> file_path
    """
    index = {}

    for module in ssat.get("modules", []):
        for file in module.get("files", []):
            path = file["path"]

            for fn in file.get("functions", []) or []:
                index[fn["name"]] = path

            for cls in file.get("classes", []) or []:
                index[cls["name"]] = path
                for m in cls.get("methods", []) or []:
                    index[m["name"]] = path

    return index

def build_file_relation_graph(ssat: dict) -> tuple[dict, dict]:
    """
    Returns:
        outgoing_index[file] -> set(related_files)
        incoming_index[file] -> set(related_files)
    """
    symbol_to_file = build_symbol_to_file_index(ssat)

    outgoing = {}
    incoming = {}

    def add_edge(src, dst):
        if src == dst:
            return
        outgoing.setdefault(src, set()).add(dst)
        incoming.setdefault(dst, set()).add(src)

    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            src_file = file["path"]

            # file-level imports
            for imp in (file.get("realized_relations", {}).get("imports", []) or []):
                if imp in symbol_to_file:
                    add_edge(src_file, symbol_to_file[imp])

            # function calls
            for fn in (file.get("functions") or []):
                for callee in (fn.get("realized_relations", {}).get("calls", []) or []):
                    if callee in symbol_to_file:
                        add_edge(src_file, symbol_to_file[callee])

            # method calls
            for cls in (file.get("classes") or []):
                for m in (cls.get("methods") or []):
                    for callee in (m.get("realized_relations", {}).get("calls", []) or []):
                        if callee in symbol_to_file:
                            add_edge(src_file, symbol_to_file[callee])

    return outgoing, incoming

def build_code_index(init_code: list[dict]) -> dict:
    """
    Build path -> code index from generated code list.

    init_code item format:
    {
        "path": str,
        "code": str
    }
    """
    index = {}
    for item in init_code:
        path = item.get("path")
        if path:
            index[path] = item.get("code", "")
    return index

def collect_related_file_codes(
    related_files: set[str],
    init_code: list[dict]
) -> list[dict]:
    """
    Collect code content for related files.

    Returns:
    [
        {
            "path": str,
            "code": str
        }
    ]
    """
    code_index = build_code_index(init_code)

    results = []
    for path in sorted(related_files):
        if path in code_index:
            results.append({
                "path": path,
                "code": code_index[path]
            })

    return results

def format_related_codes_as_context(
    related_file_codes: list[dict]
) -> str:
    """
    Format related file codes into a single LLM-friendly text block.
    """
    blocks = []

    for item in related_file_codes:
        blocks.append(
            f"### File: {item['path']}\n"
            f"{item['code']}"
        )

    return "\n\n".join(blocks)


# update the realized relations in iterative generation
def safe_parse_ast(code: str):
    try:
        return ast.parse(code)
    except SyntaxError:
        return None
    
def extract_imported_modules(tree: ast.AST) -> Set[str]:
    modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])

    return modules

def module_to_file_path(module: str, code_index: Dict[str, dict]) -> Optional[str]:
    for path in code_index.keys():
        if path.endswith(f"{module}.py"):
            return path
    return None

def update_realized_relations_from_code(
    target_path: str,
    code: str,
    outgoing_index: Dict[str, set],
    incoming_index: Dict[str, set],
    code_index: Optional[Dict[str, dict]] = None,
) -> Tuple[Dict[str, set], Dict[str, set]]:

    if code_index is None:
        code_index = {}

    old_outgoing = outgoing_index.get(target_path, set())

    for dep in old_outgoing:
        if dep in incoming_index:
            incoming_index[dep].discard(target_path)

    outgoing_index[target_path] = set()

    tree = safe_parse_ast(code)
    if tree is None:
        return outgoing_index, incoming_index

    imported_modules = extract_imported_modules(tree)

    for module in imported_modules:
        dep_path = module_to_file_path(module, code_index)
        if dep_path is None or dep_path == target_path:
            continue

        outgoing_index.setdefault(target_path, set()).add(dep_path)
        incoming_index.setdefault(dep_path, set()).add(target_path)

    return outgoing_index, incoming_index


def extract_functions_and_classes(tree: ast.AST) -> Dict[str, list]:
    functions = []
    classes = []

    for node in tree.body:
        # -------- global function --------
        if isinstance(node, ast.FunctionDef):
            functions.append({
                "name": node.name,
                "description": ast.get_docstring(node) or "",
                "parameters": [
                    {
                        "name": arg.arg,
                        "type": "Any",
                        "description": ""
                    }
                    for arg in node.args.args
                ],
                "return_type": "Any"
            })

        # -------- class --------
        elif isinstance(node, ast.ClassDef):
            cls = {
                "name": node.name,
                "description": ast.get_docstring(node) or "",
                "attributes": [],
                "methods": []
            }

            for item in node.body:
                # class attribute
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            cls["attributes"].append({
                                "name": target.id,
                                "type": "Any",
                                "description": ""
                            })

                # class method
                elif isinstance(item, ast.FunctionDef):
                    cls["methods"].append({
                        "name": item.name,
                        "description": ast.get_docstring(item) or "",
                        "parameters": [
                            {
                                "name": arg.arg,
                                "type": "Any",
                                "description": ""
                            }
                            for arg in item.args.args
                            if arg.arg != "self"
                        ],
                        "return_type": "Any"
                    })

            classes.append(cls)

    return {
        "functions": functions,
        "classes": classes
    }

def find_or_create_file_node(
    ssat: Dict,
    path: str,
    description: str
) -> Dict:
    """
    Find existing file node, or create a new one under a default module.
    """

    # ---- try to find ----
    for module in ssat.get("modules", []):
        for file in (module.get("files") or []):
            if file.get("path") == path:
                file["description"] = description
                return file

    # ---- not found: create ----
    # strategy: use top-level directory as module name
    module_name = path.split("/")[0] if "/" in path else "default"

    for module in ssat["modules"]:
        if module["name"] == module_name:
            target_module = module
            break
    else:
        target_module = {
            "name": module_name,
            "description": f"Auto-created module for {module_name}",
            "files": []
        }
        ssat["modules"].append(target_module)

    file_node = {
        "name": path.split("/")[-1],
        "path": path,
        "description": description,
        "global_code": {
            "globalVariables": [],
            "globalBlocks": []
        },
        "classes": [],
        "functions": []
    }

    target_module["files"].append(file_node)
    return file_node

def update_ssat_realized_from_code(
    ssat: Dict,
    file_result: Dict
) -> Dict:
    """
    Update SSAT in-place based on newly generated code.

    file_result:
        {
            "path": str,
            "code": str,
            "description": str
        }
    """

    path = file_result["path"]
    code = file_result.get("code", "")
    description = file_result.get("description", "")

    # ---- 1. find or create file node ----
    file_node = find_or_create_file_node(
        ssat,
        path=path,
        description=description
    )

    # ---- 2. parse code ----
    tree = safe_parse_ast(code)
    if tree is None:
        # keep file node but do not update structure
        return ssat

    extracted = extract_functions_and_classes(tree)

    # ---- 3. overwrite structure ----
    file_node["functions"] = extracted["functions"]
    file_node["classes"] = extracted["classes"]
    
    return ssat

def remove_file_from_ssat(ssat: dict, target_path: str) -> dict:
    """
    Remove a file (by path) from SSAT.
    SSAT structure:
      ssat["modules"] -> list of modules
      module["files"] -> list of files

    This function modifies ssat in place and also returns it.
    """

    modules = ssat.get("modules", [])
    if not isinstance(modules, list):
        return ssat

    for module in modules:
        files = (module.get("files") or [])
        if not isinstance(files, list):
            continue

        new_files = [
            f for f in files
            if f.get("path") != target_path
        ]

        if len(new_files) != len(files):
            module["files"] = new_files
            break  

    return ssat

