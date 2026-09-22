import ast
from pathlib import Path

from worker import app


def test_cloud_worker_keeps_local_api_routes() -> None:
    api_dir = Path(__file__).parents[2] / "backend" / "app" / "api"
    expected: set[tuple[str, str]] = set()
    for source in api_dir.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        prefix = ""
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
                if isinstance(node.value, ast.Call):
                    prefix = next((keyword.value.value for keyword in node.value.keywords if keyword.arg == "prefix"), "")
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.upper()
                    if method in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
                        path = decorator.args[0].value if decorator.args else ""
                        expected.add((method, prefix + path))
    actual = {
        (method.upper(), path)
        for path, methods in app.openapi()["paths"].items()
        for method in methods
        if path.startswith("/api/")
    }
    assert expected <= actual
