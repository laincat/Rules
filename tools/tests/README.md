# Test setup

Use Python 3.13, matching CI. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m unittest discover -s tools/tests -v
python -m unittest discover -s .github/scripts -v
```

Windows: activate with `.venv\Scripts\Activate.ps1` in PowerShell instead.
The changelog guards run without third-party Python packages. The broader historical test suite may exercise existing source retrieval paths.

Changelog tests validate source parsing, seven-day filtering, translation caching, generated-page structure and failure retention. They do not replace live Surge or mihomo networking tests.
