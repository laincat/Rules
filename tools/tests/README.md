# Test setup

Use Python 3.13, matching CI. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r tools/tests/requirements.txt
python -m unittest discover -s tools/tests -v
python -m unittest discover -s .github/scripts -v
```

Windows: activate with `.venv\Scripts\Activate.ps1` in PowerShell instead.
Dependency installation requires package-index access (or a prepared wheel cache). Documentation guards run without network access once dependencies are installed. The broader historical test suite may exercise existing source retrieval paths.

Documentation tests validate source-map ownership, local links, independent generated text, YAML example parsing and watcher migration behavior. They do not replace application-level Surge or Docker/TUN networking tests.
