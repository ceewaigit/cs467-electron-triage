# Five old failures, latest configuration

The user requested one new coding-assistant run of the five old dry-run failures with the
latest committed configuration. The subsequent authorized live attempt failed on workspace
authentication before inference, so this free fallback continues independently.

Use source `7debabe981d26af3ff36cc4606f45bc6efb1daf3` without edits. The five selected cases are
e52255, e52266, e52385, e52463 and e53734. Their frozen expectations and inputs remain unchanged.
Prepare one opaque input-only workspace per case and give each to a fresh assistant without
parent conversation history, old decisions, expected outcomes or grading documents.

Each assistant reads the displayed configuration and issue, uses the unchanged helper scripts,
and records exactly one first decision. Preserve every helper call, rejection and final
proposal. No external provider calls, workflow dispatches or issue writes are permitted.
This uses existing Codex access; its exact inherited backend ID and metered usage are unavailable.

Seal all five proposals before scoring with the frozen scorer. A fresh independent checker
must calculate results and inspect decisions before reading the coordinator's result or
submission conclusion. It should report remaining errors, annotation disagreements, evidence
limits and any work genuinely needed before submission. Do not change policy or expectations
in response to these golden cases and do not rerun a failed decision to obtain a pass.

These cases were chosen because they failed before. A single new trial does not prove the
change caused a difference or that other cases cannot regress. Keep the original 20/25 result
and all five original failures intact. Do not combine new outcomes with the other 20 old
passes to claim a new 25-case evaluation. This is separate from configured Claude and the
90-run hosted plan, which remains pending.
