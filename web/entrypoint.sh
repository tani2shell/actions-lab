#!/bin/sh
set -eu
# local flag: owned by ci, mode 600 (RCE foothold user can read it)
printf '%s\n' "$LOCAL_FLAG" > /home/ci/local.txt
chown ci:ci /home/ci/local.txt
chmod 600 /home/ci/local.txt

# runner credential lives root:ci 640 — readable only after foothold
mkdir -p /etc/forgeci
printf 'FORGECI_RUNNER_TOKEN=%s\n' "$FORGECI_RUNNER_TOKEN" > /etc/forgeci/runner.env
chown root:ci /etc/forgeci/runner.env
chmod 640 /etc/forgeci/runner.env

# decoy: stale legacy token (queue rejects it)
printf 'FORGECI_LEGACY_TOKEN=rt_LEGACY_0000000000000000000000000000000f\n' > /etc/forgeci/legacy.token
chown root:ci /etc/forgeci/legacy.token
chmod 640 /etc/forgeci/legacy.token

# seed hook log so the tail-render feature has history
printf '[hook] prepared commit: initial import @ seed\n' >> /srv/forgeci/hooks.log
chown ci:ci /srv/forgeci/hooks.log

# reforge v2: strip secrets from the runtime process env AFTER the files
# above are written — foothold `env`/`/proc/1/environ` must come up empty.
unset LOCAL_FLAG FORGECI_RUNNER_TOKEN

exec su -s /bin/sh ci -c "cd /app && exec python3 app.py"
