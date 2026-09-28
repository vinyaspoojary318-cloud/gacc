"""Plain-English intent parsing for gacc."""
from __future__ import annotations

import re


def parse_natural(text: str) -> tuple[str, dict] | None:
    t = text.strip().lower()
    t = re.sub(r"[\"'`]", "", t)
    t = re.sub(r"\s+", " ", t)

    if re.search(
        r"\b(status|who am i|current account|which account|active account)\b", t
    ):
        return "status", {}

    if re.search(
        r"\b(check|right account|wrong account|am i on|correct account)\b", t
    ):
        return "check", {}

    if re.search(
        r"\b(list|show|see)\b.*\b(accounts?|users?|logins?)\b"
        r"|\b(accounts?|users?)\b.*\b(list|show)\b"
        r"|\bmy accounts\b",
        t,
    ):
        return "list", {}

    if re.search(
        r"\b(login|log in|sign in|authenticate|add account|new account)\b", t
    ):
        return "login", {}

    if re.search(r"\b(ship|publish|deploy this|push this)\b", t):
        public = bool(re.search(r"\bpublic\b", t))
        name = None
        m = re.search(r"(?:called|named|name)\s+([a-zA-Z0-9._-]+)", t)
        if m:
            name = m.group(1)
        account = None
        m = re.search(
            r"(?:with|using|under|as)\s+(?:account\s+)?([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
            t,
        )
        if m:
            account = m.group(1)
        return "ship", {"name": name, "public": public, "account": account}

    m = re.search(
        r"(?:switch|use|change|set)\s+(?:to\s+)?(?:account\s+)?([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
        t,
    )
    if m and not re.search(r"\b(repo|project|repository)\b", t):
        return "use", {"username": m.group(1)}

    m = re.search(
        r"(?:account|user)\s+([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
        t,
    )
    if m and re.search(r"\b(switch|use|change|set)\b", t):
        return "use", {"username": m.group(1)}

    if re.search(r"\b(create|make|new|init)\b", t) and re.search(
        r"\b(repo|repository|project)\b", t
    ):
        public = bool(re.search(r"\bpublic\b", t))
        if re.search(r"\bprivate\b", t):
            public = False

        name = None
        for pat in (
            r"(?:called|named|name)\s+([a-zA-Z0-9._-]+)",
            r"(?:repo|repository|project)\s+(?:called\s+|named\s+)?([a-zA-Z0-9._-]+)",
            r"(?:create|make|new)\s+([a-zA-Z0-9._-]+)(?:\s+repo|\s+repository|\s+project)?",
        ):
            m = re.search(pat, t)
            if m:
                candidate = m.group(1)
                if candidate not in (
                    "a",
                    "an",
                    "the",
                    "public",
                    "private",
                    "repo",
                    "repository",
                    "project",
                ):
                    name = candidate
                    break

        account = None
        m = re.search(
            r"(?:with|using|under|as)\s+(?:account\s+)?([a-zA-Z0-9][a-zA-Z0-9-]{0,38})",
            t,
        )
        if m:
            account = m.group(1)

        description = None
        m = re.search(
            r"(?:description|desc|about)\s+[\"']?(.+?)[\"']?\s*$",
            text.strip(),
            re.I,
        )
        if m:
            description = m.group(1).strip()

        return "create", {
            "name": name,
            "public": public,
            "account": account,
            "description": description,
        }

    if re.search(r"\b(version|help|what can you do|how do i)\b", t):
        return "help", {}

    return None
