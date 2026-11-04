"""ForgeCI job-queue / runner service.

Runs as root on its own box. Holds the shared runner token's trust realm:
any holder of the token can read every tenant's job logs and artifacts.
Artifact download joins a caller-supplied rel path onto the job dir.
"""
import json
import os
import re
import threading
import time
import uuid

from flask import Flask, jsonify, request
from werkzeug.serving import WSGIRequestHandler

RUNNER_ENV_PATH = "/etc/forgeci/runner.env"
ART_BASE = "/srv/queue/artifacts"
JOBS_DIR = "/srv/queue/jobs"


def _load_runner_token(path=RUNNER_ENV_PATH):
    """Token lives in a root-only file (mode 600), NOT in process env
    (reforge v2: /proc/1/environ one-shot must not yield the secrets)."""
    try:
        with open(path) as fh:
            for line in fh:
                if line.startswith("FORGECI_RUNNER_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


RUNNER_TOKEN = _load_runner_token()

app = Flask(__name__)

TOKEN_RE = re.compile(r"^rt_[0-9a-f]{32}$")


class QuietHandler(WSGIRequestHandler):
    def version_string(self):
        return "forgeci-httpd"

    def log_request(self, *args, **kwargs):
        pass


def auth_ok():
    """Returns (ok, error_json). Presence-but-wrong gets a format hint."""
    hdr = request.headers.get("Authorization", "")
    if not hdr:
        return False, {"error": "missing authorization",
                      "hint": "Authorization: Bearer <runner token>"}
    token = hdr.removeprefix("Bearer ").strip()
    if RUNNER_TOKEN and token == RUNNER_TOKEN:
        return True, None
    shape = "shape ok" if TOKEN_RE.match(token) else "bad shape (expect rt_ + 32 hex)"
    return False, {"error": "invalid runner token", "hint": shape}


def require_auth():
    ok, err = auth_ok()
    return (jsonify(err), 401) if not ok else None


@app.get("/")
def index():
    return jsonify(service="forgeci-queue",
                   endpoints=["/api/v1/jobs (POST)",
                             "/api/v1/jobs/<id>/log (GET)",
                             "/api/v1/artifacts/<job_id>?rel=<path> (GET)"],
                   auth="bearer runner token")


@app.get("/healthz")
def healthz():
    return jsonify(ok=True, service="forgeci-queue", t=time.time())


@app.get("/api/v1/jobs")
def list_jobs():
    bad = require_auth()
    if bad:
        return bad
    out = []
    for fn in sorted(os.listdir(JOBS_DIR)):
        if fn.endswith(".json"):
            with open(f"{JOBS_DIR}/{fn}") as fh:
                j = json.load(fh)
            out.append({"job_id": j["job_id"], "repo": j["repo"],
                        "status": j["status"]})
    # seeded tenant history (nightly backups run outside this API)
    for job_id in sorted(os.listdir(ART_BASE)):
        if not any(o["job_id"] == job_id for o in out):
            out.append({"job_id": job_id, "repo": "acme/infra",
                        "status": "succeeded"})
    return jsonify(jobs=out)


@app.post("/api/v1/jobs")
def create_job():
    bad = require_auth()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    job_id = "JOB-" + uuid.uuid4().hex[:4].upper()
    job = {
        "job_id": job_id,
        "repo": body.get("repo", "unknown"),
        "branch": body.get("branch", "?"),
        "message": body.get("message", ""),
        "status": "queued",
        "created": time.time(),
    }
    with open(f"{JOBS_DIR}/{job_id}.json", "w") as fh:
        json.dump(job, fh)
    threading.Thread(target=_finish_job, args=(job_id,), daemon=True).start()
    return jsonify(job_id=job_id, status="queued"), 201


def _finish_job(job_id):
    time.sleep(5)
    path = f"{JOBS_DIR}/{job_id}.json"
    with open(path) as fh:
        job = json.load(fh)
    job["status"] = "succeeded"
    with open(path, "w") as fh:
        json.dump(job, fh)
    art = f"{ART_BASE}/{job_id}"
    os.makedirs(art, exist_ok=True)
    with open(f"{art}/stdout.txt", "w") as fh:
        fh.write(f"checkout {job['branch']} ok\nbuild ok for {job['repo']}\n")


@app.get("/api/v1/jobs/<job_id>/log")
def job_log(job_id):
    bad = require_auth()
    if bad:
        return bad
    path = f"{JOBS_DIR}/{job_id}.json"
    if not os.path.isfile(path):
        return jsonify(error="no such job"), 404
    with open(path) as fh:
        job = json.load(fh)
    log = (f"[queue] accepted {job['job_id']} repo={job['repo']} "
           f"branch={job['branch']}\n"
           f"[runner] message: {job['message']}\n"
           f"[runner] status: {job['status']}\n")
    return jsonify(job_id=job_id, log=log, status=job["status"])


@app.get("/api/v1/artifacts/<job_id>")
def artifact(job_id):
    bad = require_auth()
    if bad:
        return bad
    rel = request.args.get("rel")
    if rel is None:
        return jsonify(error="missing ?rel=",
                       hint="artifact path relative to the job dir"), 400
    job_dir = os.path.join(ART_BASE, job_id)
    if not os.path.isdir(job_dir):
        return jsonify(error="no such job artifacts"), 404
    # reforge v2: containment guard — after joining, the resolved path must
    # stay inside the artifacts root. Blocks `../` escapes AND absolute-path
    # joins (os.path.join("/a", "/etc") == "/etc").
    target = os.path.realpath(os.path.join(job_dir, rel))
    art_root = os.path.realpath(ART_BASE)
    if target != art_root and not target.startswith(art_root + os.sep):
        return jsonify(error="artifact outside artifact root",
                       hint="rel must stay under /srv/queue/artifacts"), 400
    if not os.path.isfile(target):
        return jsonify(error="artifact not found"), 404
    with open(target, "rb") as fh:
        data = fh.read()
    return app.response_class(data, mimetype="application/octet-stream")


if __name__ == "__main__":
    os.makedirs(JOBS_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=8081, request_handler=QuietHandler)
