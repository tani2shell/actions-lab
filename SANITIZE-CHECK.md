# SANITIZE-CHECK — actions-lab

Scan date: 2026-11-04 · Scanner: forge (outbound gate 1) · Standard: GITHUB-PLAN §3
Method: programmatic grep of the full package tree (excluding `.git`, this file, and binary image assets) against each banned-category pattern; whitelist = business-word false positives listed below. This file names the patterns, so it is excluded from its own scan.

| category | result |
|---|---|
| avatar names (Rook/Beaver/Owl/Magpie/Tani/Yungang) | **PASS** (0 hits) |
| kanban card ids (t_xxxxxxxx) | **PASS** (0 hits) |
| LEDGER internal history (uppercase) | **PASS** (0 hits) |
| local paths (/Users/m5, ~/pentest) | **PASS** (0 hits) |
| internal IPs (192.168.x) | **PASS** (0 hits) |
| host-service fingerprints (WeKnora/hindsight/hermes) | **PASS** (0 hits) |
| audit-key material | **PASS** (0 hits) |

| structural item | result |
|---|---|
| required docs present | **PASS** |
| RESET script present + executable | **PASS** (RESET.sh) |
| RESET script syntax (bash -n) | **PASS** |
| audit-key*.json physically absent | **PASS** |

## Whitelisted business words (not leaks)
- `tani2shell` — the public GitHub owner handle itself.
- `knowledge` / `acknowledgement` — substring matches for the name pattern 'Owl'.
- lowercase `ledger` in wallet/loyalty feature code & schema (VoltMart) — domain vocabulary; the banned marker is the uppercase internal war-ledger `LEDGER`.

## Flags published with the WT (public by policy)

- `FLAG{alx_local_866ee5a4f6afdc12}`
- `FLAG{alx_local_<16 hex>}`
- `FLAG{alx_proof_872cc49c98352ddc}`
- `FLAG{alx_proof_<16 hex>}`

Gate-2 re-check belongs to the publishing proxy (media) before each `git push`.
