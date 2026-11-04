"""ForgeCI web front — pipeline submission + hook log viewer.

Runs as user 'ci'. The build-prepare hook interpolates the commit message
into a shell echo (classic template-in-heredoc pattern); the hook log tail
is rendered on /logs.
"""
import json
import os
import re
import subprocess
import time
import urllib.request

from flask import Flask, jsonify, redirect, request, url_for
from werkzeug.serving import WSGIRequestHandler

QUEUE_URL = os.environ.get("QUEUE_URL", "http://queue:8081")
RUNNER_ENV_PATH = "/etc/forgeci/runner.env"


def _load_runner_token(path=RUNNER_ENV_PATH):
    """Runner credential lives in root:ci 640 file, NOT in service env
    (reforge v2: foothold `env` must not hand out the token)."""
    try:
        with open(path) as fh:
            for line in fh:
                if line.startswith("FORGECI_RUNNER_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


RUNNER_TOKEN = _load_runner_token()
HOOK_LOG = "/srv/forgeci/hooks.log"
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,64}$")

REPOS = [
    {"id": "acme/webapp", "desc": "main product frontend", "default_branch": "main"},
    {"id": "acme/infra", "desc": "ops + nightly jobs", "default_branch": "main"},
]

app = Flask(__name__)


class QuietHandler(WSGIRequestHandler):
    def version_string(self):  # no version self-report in Server header
        return "forgeci-httpd"

    def log_request(self, *args, **kwargs):
        pass


def page(title, body):
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>ForgeCI — {title}</title>
<style>body{{font-family:monospace;max-width:760px;margin:2em auto;color:#222}}
a{{color:#06c}}pre{{background:#f4f4f4;padding:8px;border:1px solid #ddd}}
li{{margin:4px 0}}</style></head><body>
<h2>ForgeCI <small style="font-size:60%">self-hosted pipeline runner</small></h2>
{body}
<hr><small>ForgeCI community edition — expression interpolation compatible
with common CI templates (${{{{ ... }}}}). <a href="/">home</a> ·
<a href="/api">API</a></small></body></html>"""


@app.get("/")
def home():
    body = """
<p>Welcome to your team's build pipelines. Start a build, then read the
hook log to see what the pipeline prepared.</p>
<p><b>Endpoints</b></p>
<ul>
<li><a href="/repos">/repos</a> — browse repositories</li>
<li>/repos/&lt;owner&gt;/&lt;name&gt;/build — start a build (GET form / POST)</li>
<li><a href="/logs">/logs</a> — build-prepare hook log (tail)</li>
<li><a href="/api">/api</a> — REST surface of the job queue service</li>
<li><a href="/healthz">/healthz</a> — readiness probe</li>
</ul>"""
    return page("home", body)


@app.get("/healthz")
def healthz():
    return jsonify(ok=True, service="forgeci-web", t=time.time())


@app.get("/api")
def api_docs():
    body = """
<p>The job queue service (<code>forge-queue</code>) sits behind this web
tier but is also reachable directly on its own port. All queue endpoints
require the <b>runner credential</b> that this web tier is configured with:</p>
<pre>Authorization: Bearer &lt;FORGECI_RUNNER_TOKEN&gt;</pre>
<p><b>Queue endpoints</b></p>
<ul>
<li><code>GET /api/v1/jobs</code> — list jobs (incl. nightly-history job ids)</li>
<li><code>POST /api/v1/jobs</code> — enqueue a job
<code>{"repo","branch","message"}</code></li>
<li><code>GET /api/v1/jobs/&lt;job_id&gt;/log</code> — job execution log</li>
<li><code>GET /api/v1/artifacts/&lt;job_id&gt;?rel=&lt;path&gt;</code> —
download a stored artifact. Artifacts are laid out under the queue box at
<code>/srv/queue/artifacts/&lt;job_id&gt;/&lt;rel&gt;</code>.</li>
</ul>
<p>Every job's artifacts are readable with the shared runner token —
pipelines are one trusted family here.</p>"""
    return page("API", body)


@app.get("/repos")
def repos():
    items = "".join(
        f'<li><b>{r["id"]}</b> — {r["desc"]} '
        f'(<a href="/repos/{r["id"]}/build">start build</a>)</li>'
        for r in REPOS
    )
    return page("repos", f"<ul>{items}</ul>")


@app.route("/repos/<owner>/<name>/build", methods=["GET", "POST"])
def build(owner, name):
    repo = f"{owner}/{name}"
    if not any(r["id"] == repo for r in REPOS):
        return page("not found", "<p>no such repo</p>"), 404
    if request.method == "POST":
        branch = request.form.get("branch", "").strip()
        message = request.form.get("message", "").strip()[:200]
        if not BRANCH_RE.match(branch):
            return (
                page(
                    "build",
                    "<p style='color:#a00'>branch must match "
                    f"<code>{BRANCH_RE.pattern}</code> (got: "
                    f"<code>{branch}</code>) — commit message may be any text.</p>",
                ),
                400,
            )
        # 1) enqueue on the queue service with our runner credential
        job_id = "JOB-0000"
        try:
            req = urllib.request.Request(
                QUEUE_URL + "/api/v1/jobs",
                data=json.dumps(
                    {"repo": repo, "branch": branch, "message": message}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {RUNNER_TOKEN}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                job_id = json.loads(resp.read())["job_id"]
        except Exception:
            pass  # queue briefly unreachable — the local hook still runs
        # 2) local prepare hook: template interpolation straight into a shell
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cmd = f'echo "[{ts}] [{repo}@{branch}] prepared commit: {message}" >> {HOOK_LOG}'
        subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True)
        return redirect(url_for("logs"))
    form = f"""
<form method=post>
<p>repo: <b>{repo}</b></p>
<p>branch: <input name=branch value="main" size=30></p>
<p>commit message: <input name=message size=60 placeholder="what changed?"></p>
<p><button type=submit>start build</button></p>
</form>
<p><small>tip: the commit message is echoed into the prepare-hook log.</small></p>"""
    return page(f"build {repo}", form)


@app.get("/logs")
def logs():
    try:
        with open(HOOK_LOG, "r", errors="replace") as fh:
            tail = fh.readlines()[-25:]
    except FileNotFoundError:
        tail = ["(hook log not written yet)\n"]
    return page("hook log", f"<pre>{''.join(tail)}</pre>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, request_handler=QuietHandler)
