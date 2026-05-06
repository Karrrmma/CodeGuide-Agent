from pathlib import Path


IGNORE_NAMES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "__pycache__",
    "venv",
    ".venv",
    ".env",
    ".env.local",
    "coverage",
    ".DS_Store",
}


def should_ignore(path: Path) -> bool:
    return any(part in IGNORE_NAMES for part in path.parts)


def ensure_inside_project(root: Path, target: Path) -> None:
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("Cannot access files outside the project folder.")


def list_files(project_path: str) -> list[str]:
    root = Path(project_path).resolve()
    files = []

    for path in root.rglob("*"):
        if should_ignore(path):
            continue

        if path.is_file():
            files.append(str(path.relative_to(root)))

    return files


def read_file(project_path: str, file_path: str) -> str:
    root = Path(project_path).resolve()
    target = (root / file_path).resolve()

    ensure_inside_project(root, target)

    if should_ignore(target):
        raise ValueError("This file is ignored for safety.")

    return target.read_text(encoding="utf-8", errors="ignore")


def search_code(project_path: str, query: str) -> list[dict]:
    root = Path(project_path).resolve()
    results = []

    for file in list_files(project_path):
        path = root / file

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if query.lower() in line.lower():
                results.append({
                    "file": file,
                    "line": line_number,
                    "text": line.strip(),
                })

    return results
