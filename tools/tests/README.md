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

Sukka provider validation (after generating with the same official Mihomo core):

```sh
python tools/validate_sukka.py --mihomo ./mihomo
```

This copies the generated providers into an isolated temporary core home, checks
that the example references every artifact, and loads them as local file providers.
It starts only a loopback controller, with proxy listeners, DNS and TUN disabled.
Classical YAML rule counts must match the payload so silently skipped rows fail
validation. MRS files are also decoded and loaded by the real core. CI runs this
check and the regression suite again after generation, before publishing.
IP-ASN parsing may retrieve the official MetaCubeX ASN database; pass
`--asn-mmdb /path/to/ASN.mmdb` to use an existing copy for offline validation.
Set `MIHOMO` (and optionally `MIHOMO_ASN`) when running unit tests to include
the real-core positive and negative integration tests.
