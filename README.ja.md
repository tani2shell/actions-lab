# actions-lab（日本語）

本編は [README.md](README.md)（英語）。要点のみ:

- **ジャンル**: CI/CD — コミットメッセージ経由でビルド機に足場 → 共有ランナートークン回収 → アーティファクト庫をクロステナントで読む三段連鎖。
- **起動**: `./gen-secrets.sh` → `docker compose up -d --build` → `http://127.0.0.1:18930`（キュー API `http://127.0.0.1:18931` も公開）
- **リセット**: `./RESET.sh`
- **フラグ**: 2 枚（ビルド機の `local.txt` / キュー箱のアーティファクト庫内の `proof.txt`）
- **難易度**: 2.5–3/5（AI ペンテストエージェント実戦較正済み、`DIFFICULTY.md` 参照）
- 問題文（ネタバレなし）は `CHALLENGE.md`、解答は `SOLUTION.md`。
