# Browser-only demo (GitHub Pages)

Static build of the Duplicate Citizen Detection dashboard. The unchanged Python files from `main`
run inside the browser through stlite (Pyodide). Rebuild: `python build.py <path-to-main-checkout>`.

- Records live only in the visitor's browser (IndexedDB). They are not shared between devices or people.
- The FastAPI REST API and API-key auth are not part of this version (a static page has no server).
- `rapidfuzz` is replaced by a pure-Python equivalent of `token_sort_ratio` (`shim/`), tested identical to rapidfuzz 3.14.5.
- One text patch: the sidebar caption describing the server version.
- Fictional demo data only.
