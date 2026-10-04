"""Validation for DNS list inputs, without converting URL rules to domains."""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re

LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")
HTML_START = re.compile(r"<(?:!doctype\s+html|html|head|body)\b", re.I)


def _dns_name(value: str, require_dot: bool = True) -> str | None:
    value = value.strip().removesuffix(".").lower()
    if not value or any(c in value for c in "/\\:*^$@# \t\r\n"):
        return None
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if len(value) > 253 or (require_dot and "." not in value):
        return None
    labels = value.split(".")
    if labels[-1].isdigit():
        return None
    for label in labels:
        if (not label or len(label) > 63 or label.startswith("-")
                or label.endswith("-") or not LABEL_CHARS.issuperset(label)):
            return None
        if label.startswith("xn--"):
            try:
                # Preserve valid A-labels, including IDNA2008 labels not round-trippable
                # through Python's IDNA2003 codec.
                label[4:].encode("ascii").decode("punycode")
            except UnicodeError:
                return None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    return None


def normalize_domain(value: str) -> str | None:
    return _dns_name(value)


def validate_source_text(url: str, text: str, content_type: str = "") -> None:
    if not text.strip():
        raise ValueError(f"empty source: {url}")
    if "html" in content_type.lower() or HTML_START.search(text[:2048]):
        raise ValueError(f"HTML response instead of rules: {url}")
    if "\ufffd" in text or "\x00" in text:
        raise ValueError(f"invalid text encoding: {url}")


@dataclass
class PublicSuffixList:
    exact: set[str] = field(default_factory=set)
    wildcard: set[str] = field(default_factory=set)
    exception: set[str] = field(default_factory=set)

    @classmethod
    def from_text(cls, text: str) -> "PublicSuffixList":
        result = cls()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            target = result.exact
            if line.startswith("!"):
                line, target = line[1:], result.exception
            elif line.startswith("*."):
                line, target = line[2:], result.wildcard
            name = _dns_name(line, require_dot=False)
            if name is None:
                raise ValueError(f"invalid public suffix rule: {raw!r}")
            target.add(name)
        if not result.exact:
            raise ValueError("empty public suffix list")
        return result

    def is_public_suffix(self, domain: str) -> bool:
        domain = domain.lower().rstrip(".")
        if domain in self.exception:
            return False
        if domain in self.exact or "." not in domain:
            return True
        return domain.split(".", 1)[1] in self.wildcard
