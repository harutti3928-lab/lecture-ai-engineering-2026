# 第3回 発展(a)：ADK版の学習支援エージェント

`glossary_agent/agent.py`で、既存の`app.agent.INSTRUCTIONS`と`app.tools`の3つの関数をそのまま使う。
モデルも`app.config.MODEL`を参照する。`AIE_MODEL`未指定時は`gemini-3.5-flash-lite`。

リポジトリ直下のPowerShellで起動する。環境変数`GEMINI_API_KEY`は設定済みであること。
キーをコードや実行記録へ書かない。

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --no-sync --with google-adk==2.14.0 adk run --in_memory adk_agent/glossary_agent
```

質問を入力してEnterで送信し、`exit`で終了する。
`--no-sync`はこのPCの既存の`.venv`を再同期しないための指定。
ADKはuvの一時環境に追加され、`pyproject.toml`・`uv.lock`は変更しない。
`--in_memory`はセッションをローカルDBに永続化しないための指定。

記録した比較実験は、各質問を新しいプロセス・セッションで送信した。
ADK 2.14.0のCLIでは、次のように質問を引数で渡して1問だけ実行できる。
`--jsonl`はCLI既存のイベント出力であり、独自にtrace機能を実装したものではない。

```powershell
uv run --no-sync --with google-adk==2.14.0 adk run --in_memory --jsonl adk_agent/glossary_agent "LoRAとQLoRAの違いは？"
```

比較結果は`lectures/03/answer.md`、全出力は`lectures/03/results/homework_advanced_adk.json`を参照。

公式資料：

- https://adk.dev/get-started/python/
- https://adk.dev/runtime/command-line/
