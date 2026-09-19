
import ast
import os

files = ["fingerprint.py", "pattern.py", "trust.py", "ranking.py", "ml.py"]
base_dir = "cortexheal/learning/"

for f in files:
    path = os.path.join(base_dir, f)
    with open(path, "r", encoding="utf-8") as file:
        content = file.read()
        lines = content.splitlines()
        print(f"\n=========================================")
        print(f"FILE: {f} | LINES: {len(lines)}")
        print(f"=========================================")
        
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                print(f"\n{node.__class__.__name__}: {node.name}")
                if isinstance(node, ast.ClassDef):
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            doc = ast.get_docstring(sub) or "No docstring"
                            doc = "    " + doc.replace("\n", "\n    ")
                            
                            # Reconstruct signature roughly
                            args = [a.arg for a in sub.args.args]
                            print(f"  def {sub.name}({
.join(args)}):")
                            print(f"    \"\"\"\n{doc}\n    \"\"\"")
                else:
                    doc = ast.get_docstring(node) or "No docstring"
                    doc = "  " + doc.replace("\n", "\n  ")
                    args = [a.arg for a in node.args.args]
                    print(f"def {node.name}({
.join(args)}):")
                    print(f"  \"\"\"\n{doc}\n  \"\"\"")

