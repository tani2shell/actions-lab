# CHALLENGE — ForgeCI

**Entry points**: `http://<host>:18930` — the ForgeCI portal — and
`http://<host>:18931`, the job-queue service, which ops also left published.
Nothing else is.

## Brief

ForgeCI is a self-hosted pipeline runner. Two boxes, two identities:

- The portal (`GET /`) lists its own endpoints; read the pages before you
  fuzz anything.
- A build takes a **branch** and a **commit message**. Branch names pass a
  strict character-set gate; the commit message "may be any text" — the
  build form says it will be *echoed into the prepare-hook log*.
- The prepare-hook log tail is rendered at `/logs`: whatever the hook line
  wrote is what you see, verbatim.
- `/api` documents the queue service for you: the authorization header
  format, the endpoints, and where artifacts live on disk. Take it at face
  value — it is honest.
- The queue service trusts **one shared runner credential**. Its own docs
  say "pipelines are one trusted family here" and they mean it: any holder
  reads every tenant's jobs and artifacts.

You have two flags to collect:

1. **local** — a secret file on the *build* box, readable only by the
   account that runs builds.
2. **proof** — a secret file on the *queue* box, root-only, filed inside
   the artifact store.

## Ground rules / observable facts

- The portal's footer mentions CI-style expression interpolation. The
  build-prepare hook is a shell line; think about what it does with the
  text you commit.
- The build machine runs as an unprivileged user; file permissions there
  are real and worth enumerating after you land.
- The queue box is not a filesystem to brute-force — its API tells you its
  own storage layout, and the artifact endpoint will tell you when you try
  to leave it.
- Not every credential you find is current. Some doors are furniture.

Good hunting. The pipeline will happily run whatever you "committed" —
make it say something interesting.
