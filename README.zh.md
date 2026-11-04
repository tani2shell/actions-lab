# actions-lab（中文）

正文见 [README.md](README.md)（英文）。要点：

- **类型**：CI/CD —— 提交信息打进构建机落点 → 共享 runner 令牌 → 跨租户读队列机产物库，一条链。
- **启动**：`./gen-secrets.sh` 后 `docker compose up -d --build` → `http://127.0.0.1:18930`（队列 API `http://127.0.0.1:18931` 同样公开）
- **重置**：`./RESET.sh`
- **旗子**：两面（构建机上的 `local.txt` / 队列机产物库内的 `proof.txt`）
- **难度**：2.5–3/5（经 AI 渗透靶手实战标定，见 `DIFFICULTY.md`）
- 题面（零泄底）在 `CHALLENGE.md`，题解在 `SOLUTION.md`。
