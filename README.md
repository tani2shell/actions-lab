# actions-lab

![battle-tested](https://img.shields.io/badge/battle%20tested-first%20blood%20by%20an%20AI%20pentest%20agent-brightgreen)
Difficulty: **2.5–3/5 (calibrated)** · Docker Compose · 2 services

A CI/CD script-injection + shared-runner-credential trust chain in one target.
The build system will run your commit message through a real shell — and the
credential you find on the build machine is a master key on the queue box.

**EN** (this file) · [日本語](README.ja.md) · [中文](README.zh.md)

## The story

ForgeCI is the self-hosted pipeline runner a small shop grew into. Ops left
the job-queue service published "just for now", the build-prepare hook
interpolates commit messages the way CI templates taught it to, and every
pipeline shares one runner credential — *"pipelines are one trusted family
here"*, the API docs say. The docs are right. That is the problem.

## Quick start

```bash
./gen-secrets.sh              # creates .env (chmod 600) with fresh flags + runner token
docker compose up -d --build
# portal:  http://127.0.0.1:18930
# queue:   http://127.0.0.1:18931   (also published — part of the puzzle, not a leak)
# reset any time:
./RESET.sh
```

Requirements: Docker with Compose v2, plus `openssl` (used by `gen-secrets.sh`).
Budget: the whole lab fits in ≤2 vCPU / 2 GB and runs on an isolated bridge
network. Flags live only in `.env` (git-ignored); `RESET.sh` keeps them stable
across resets and regenerates them on first run.

## What's in the box

| path | role |
|---|---|
| `web/` | portal + build submission + hook-log viewer (the build box) |
| `queue/` | job-queue + artifact store (the trust-surface box) |
| `gen-secrets.sh` | seeds `.env` with your flags + runner token (600, git-ignored) |
| `compose.yml` | two services on an isolated net; publishes 18930 and 18931 |
| `RESET.sh` | deterministic teardown / rebuild / health-gate |
| `CHALLENGE.md` | black-box brief — read this first, zero spoilers |
| `SOLUTION.md` | full walkthrough (flags included) — after you give up or win |
| `DIFFICULTY.md` | nominal vs field-calibrated difficulty |

## Two flags

- **local** — sits on the *build* box, readable only by the account that runs
  builds. You need that box to run something for you first.
- **proof** — sits on the *queue* box, inside the artifact store, root-only.
  You need the shared runner credential — and then the artifact API's own
  documented layout — to reach it.

## Reset

`./RESET.sh` — tears down, re-seeds secrets if needed, rebuilds, and gates on
health. Deterministic: the target is fully reproducible from this repo.

## License / series

MIT. Part of the `<target>-lab` pentest series — targets built by a human
forge-master and field-calibrated by an AI pentest agent (first-blood and
timing data in `DIFFICULTY.md`).
