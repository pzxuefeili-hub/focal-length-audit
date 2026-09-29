# AI Assistance Log

Required by the project AI-use policy: record every substantive use of AI
(coding help, debugging, literature search support, language editing).
30 seconds per entry; the summary goes into the report's AI-use statement.
Raw blind-rating records are **never** pasted into AI tools.

| Entry ID | Phase | Tool and version | Purpose | Prompt summary | What you kept | How you verified it | Disclosure needed |
|---|---|---|---|---|---|---|---|
| 1 | Phase 1 | Kimi Work (Kimi Work desktop agent) | Repo bootstrap | Asked to reconstruct the project repo (structure, README, requirements, smoke test, protocol draft) from the prior chat history | Directory skeleton, README, requirements.txt, scripts/smoke_test.py, docs/protocol.md v1 | **Found 6 deviations vs. blueprint in v1** (focal levels, outcome definition, gate criteria, matrix numbers, stats details, compression rule); corrected in v2 | Yes — coding assistance + protocol drafting assistance |
| 2 | Phase 1 | Kimi Work (Kimi Work desktop agent) | Protocol alignment | Supplied instructor blueprint; asked to align protocol.md to it line by line | docs/protocol.md v2 — outcome definitions, RQ decision rules, frozen configs, scene texts, matrix (5,888), instrument procedures, gates | Pending — **investigator must read v2 against the blueprint once more before freezing**; every number in v2 traces to a blueprint line | Yes — protocol drafting assistance |

## Notes

- AI may write code, debug, polish text, and analyze data provided by the investigator.
- AI must never fabricate data or results; every AI-produced number/claim is verified by the investigator.
- Verify every AI-suggested citation, number, and code change yourself before use.
