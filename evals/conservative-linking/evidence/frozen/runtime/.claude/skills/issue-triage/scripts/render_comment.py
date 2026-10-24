#!/usr/bin/env python3
"""Render the triage comment from fixed templates.

Usage: python3 .claude/skills/issue-triage/scripts/render_comment.py --kinds need-repro,similar --refs 51761,52098

The agent chooses the kinds and the issue numbers; this script writes the
words. No text from the issue is copied into the comment, so an injected
instruction cannot be echoed into a public reply. The last line is the
machine-readable trailer the evaluation scores.
"""
import argparse
import json
import pathlib
import re
import sys

VERSION = "issue-triage/render_comment v3"
REPO = pathlib.Path(__file__).resolve().parents[4]
ORDER = ["security", "third-party", "site-policy", "upstream", "support", "similar", "need-repro"]
TEXT = {
    "need-repro": (
        "To look into this, a maintainer needs a way to reproduce it. Could you make a minimal example in "
        "[Electron Fiddle](https://www.electronjs.org/fiddle), save it as a gist and add the link here?"),
    "similar": "This looks like it may be the same problem as {refs}. If it is, adding your details there helps more "
               "than a separate issue. If it is different, a short note on what differs helps a maintainer decide.",
    "security": (
        "This report may describe a security vulnerability. Electron asks for these to be reported privately, "
        "not in public issues: see [SECURITY.md](https://github.com/electron/electron/blob/main/SECURITY.md) "
        "for how. Please don't add more details here."),
    "third-party": (
        "This looks like it is about an app built with Electron rather than Electron itself. Problems with a "
        "specific app are best reported to that app's developers, who can tell whether Electron is involved."),
    "site-policy": (
        "This looks like the website itself treating Electron differently (for example bot detection or "
        "blocking embedded browsers). Electron can't change that; the site's operator is the right contact."),
    "upstream": (
        "The behaviour described here seems to come from Chromium or Node.js rather than Electron's own code, "
        "so it probably needs to be fixed upstream first. Linking an upstream bug here, if there is one, helps."),
    "support": (
        "This reads like a usage question. The issue tracker is for bugs and feature requests; the "
        "[Electron Discord](https://discord.gg/electronjs) is a better place to ask."),
}


def main():
    """Validate template choices and corpus references, then print the fixed comment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--kinds", required=True)
    parser.add_argument("--refs", default="")
    args = parser.parse_args()
    kinds = [kind.strip() for kind in args.kinds.split(",") if kind.strip()]
    unknown_kinds = [kind for kind in kinds if kind not in TEXT]
    refs = [int(number) for number in re.findall(r"\d{4,6}", args.refs)][:3]
    if unknown_kinds or not kinds:
        print(f"[{VERSION}] rejected: unknown kinds {unknown_kinds}"
              if unknown_kinds else f"[{VERSION}] rejected: no kinds")
        return 1
    # Security reports must go to private disclosure; other templates can solicit
    # public reproductions or discussion, contradicting that instruction.
    if "security" in kinds and set(kinds) != {"security"}:
        print(f"[{VERSION}] rejected: 'security' must be the only kind")
        return 1
    if "similar" in kinds and not refs:
        print(f"[{VERSION}] rejected: 'similar' needs --refs")
        return 1
    corpus = map(json.loads, (REPO / "data" / "issue-corpus.jsonl").read_text().splitlines())
    # Planted adversarial rows can be searched, but must never become public issue links.
    corpus_numbers = {issue["number"] for issue in corpus if not issue.get("synthetic", False)}
    unknown_refs = [number for number in refs if number not in corpus_numbers]
    if unknown_refs:
        print(f"[{VERSION}] rejected: refs not in the issue corpus: {unknown_refs}")
        return 1
    # Code spans, so GitHub does not turn them into cross-references on electron/electron.
    links = ", ".join(f"`electron/electron#{r}`" for r in refs)
    parts = ["Thanks for the report."]
    parts += [TEXT[k].format(refs=links) for k in ORDER if k in kinds]
    parts.append("<sub>Automated first-pass triage. It can only add labels and comment; a maintainer makes every "
                 "decision, including whether this issue stays open.</sub>")
    parts.append(f"triage: kinds={','.join(k for k in ORDER if k in kinds)} refs={','.join('#' + str(r) for r in refs)}")
    print(f"[{VERSION}] ok -- post the text between the markers exactly")
    print("-----BEGIN COMMENT-----")
    print("\n\n".join(parts))
    print("-----END COMMENT-----")
    return 0


if __name__ == "__main__":
    sys.exit(main())
