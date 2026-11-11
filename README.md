# 古着くん スタジオ

メルカリの商品情報（`items/<商品ID>/item.json`）と写真（`items/<商品ID>/photos/`）から、
古着くんが紹介する縦型ショート動画（音声付き）を GitHub Actions で自動で作ります。

- 作り方：Actions →「古着くん動画を作る」→ Run workflow（商品IDは空欄でOK）
- 完成品：`outputs/<商品ID>/furugikun_<商品ID>.mp4`（台本 `script.json`、投稿文 `post.txt`）
- 音声：VOICEVOX（白上虎太郎）。動画を公開するときは「VOICEVOX:白上虎太郎」のクレジットが必要です（`post.txt` と動画内に記載済み）。
- キャラクター：`studio/assets/master_front.svg` が古着くんのマスター。変更しないこと。
