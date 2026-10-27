"""Builds index.html: the unchanged Python sources run in the browser through stlite (Pyodide).
Only one patch is applied: the sidebar caption that described the server version."""
import json, sys, pathlib
SRC = pathlib.Path(sys.argv[1])
FILES = ["app.py", "citizen/__init__.py", "citizen/config.py", "citizen/database.py",
         "citizen/demo.py", "citizen/documents.py", "citizen/matching.py", "citizen/service.py"]
OLD = "Shared SQLite storage. Optional local REST API. Human decisions, always."
NEW = "Browser-only demo: records are stored in this browser only. No REST API in this version. Human decisions, always."
files = {}
for name in FILES:
    text = (SRC / name).read_text(encoding="utf-8")
    if name == "app.py":
        assert OLD in text
        text = text.replace(OLD, NEW)
    files[name] = text
for sh in ("rapidfuzz/__init__.py", "rapidfuzz/fuzz.py"):
    files[sh] = (pathlib.Path(__file__).parent / "shim" / sh).read_text(encoding="utf-8")
files[".streamlit/config.toml"] = (SRC / ".streamlit/config.toml").read_text()
cfg = {"requirements": [], "entrypoint": "app.py", "files": files,
       "idbfsMountpoints": ["/home/pyodide/storage"]}
blob = json.dumps(cfg).replace("</", "<\\/")
html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Citizen records | Duplicate detection (browser demo)</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@1.12.0/build/stlite.css"></head>
<body><div id="root"></div>
<script type="module">
import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@1.12.0/build/stlite.js";
mount({blob}, document.getElementById("root"));
</script></body></html>"""
pathlib.Path("index.html").write_text(html, encoding="utf-8")
print(len(html))
