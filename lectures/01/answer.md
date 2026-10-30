# 第1回 解答

## 演習

- 講座に固有の質問：AIE2026の講座の宿題にある「3レベル」とは何ですか？
- モデルの回答（通常設定の1回目）：講座の詳細は不明と断ったうえで、「初級・中級・上級」という難易度別分類、AI活用の習熟度、思考の深さという複数の解釈を挙げた。資料などで確認するよう案内した。
- 用語集の正しい意味：`data/glossary.json` の `homework-levels` では「基礎（講義内容の確認）」「実装（自分でコードを書く）」「発展（調査や試行）」で、どれか1つに取り組めばその回の宿題は完了とされている。
- 比較して気づいたこと：一般的な難易度分類には近いが、講座の正確な区分や完了条件を確定できていない。具体例が豊富でも、講座の根拠に基づく回答とは限らない。
- トークン数：通常設定の1回目は入力21 / 出力628。`app/ask.py` では `response.usage_metadata` から入力・出力トークン数を表示するようにした。
- 環境：Windowsのローカル環境、uvによる仮想環境。Codespacesで作業したコードをcommit・pushし、ローカルの `lec01` に取り込んだ。変更後のテストはCodespacesで11件成功。

## 宿題

- 取り組んだレベル：基礎
- 実施日：2026-10-29（日本時間）
- 使用モデル：`gemini-3.5-flash-lite`
- やったこと：同じ質問を通常設定（temperature未指定）で3回、`temperature=0.2` を指定して3回実行し、回答とトークン数を保存して比較した。会話履歴・用語集・検索結果はモデルに渡していない。通常設定のtemperatureの値は取得していないため、具体的な値は不明。
- 実行方法：講座の `app.ask` と同じ `google.genai.Client` と `models.generate_content` を利用し、比較用スクリプトで設定を切り替えた。生の結果は `experiment_results.json` に保存した。
- AIツールの利用：Codexがローカル環境でAPI実験を実行し、回答と用語集を比較して、この解答の作成を支援した。

### 通常設定の結果

- 1回目：入力21 / 出力628。難易度・AI活用・思考の深さという3パターンを提示した。
- 2回目：入力21 / 出力445。難易度別の分類を中心に説明し、別の解釈もあり得ると補足した。
- 3回目：入力21 / 出力468。難易度別の分類を中心に、AIツールの操作や実務的なアウトプットを例示した。

同じ質問でも、挙げる分類の数、具体例、説明の長さが変わった。いずれも講座の正確な区分を示すのではなく、一般論や推測を含んでいた。

### temperature=0.2を指定した結果

- 1回目：入力21 / 出力761。難易度、思考の深さ、選択式の宿題という3パターンを提示した。
- 2回目：入力21 / 出力506。課題の難易度と、自己評価用のスキルレベルという2パターンを提示した。
- 3回目：入力21 / 出力607。難易度別分類を中心に説明し、「基本はレベル1から順に」と助言した。これは、どれか1つで完了する講座のルールを正確に伝えるものではない。

設定を指定しても回答の構成や長さは同一にならず、講座の正確なルールを説明できるようにはならなかった。APIは設定を含むリクエストに成功したが、その設定が内部で実際に反映されたかまでは確認できない。

### 別モデルでの試行と制約

最初に `gemini-3.8-flash` でも同じ質問を3回試したが、3回とも503エラーで回答を取得できなかった。代替の `gemini-3.1-flash-lite` も最初の試行が503だったため、その比較は中止した。これらの結果からモデルの性能差を判断することはできない。最終的には、回答を取得できたモデルでtemperatureの指定有無を比較した。

### 気づき・疑問

- 詳細で流暢な説明でも、講座固有の情報として正しいとは限らない。回答が推測であることを断っている箇所と、一般論を強く言い切る箇所を分けて読む必要がある。
- 今回はtemperatureの指定だけで、与えていない講座資料の内容を正確に説明できるようにはならなかった。正確な回答には、用語集などの根拠を渡す方法が必要だと考えた。
- 各条件3回という少数の試行であり、通常設定のtemperature値も不明なので、出力の差をtemperatureの効果と断定できない。
- APIには回答の違いだけでなく、混雑して回答が返らない場合もある。成功した結果と失敗した結果の両方を記録する必要がある。

## 補足：ターミナルでモデルと温度を変える方法

以下は再実行するための操作例。上に記録した実験結果を追加・更新するものではない。演習資料の14・16ページ（宿題とモデルの切り替え）、宿題資料の提出ルールを参照した。

### 1. 準備（WindowsのPowerShell）

VS Codeの「ターミナル → 新しいターミナル」を開き、PowerShellで次を実行する。行頭の `PS C:\...>` は入力しない。以降の例は、環境変数 `GEMINI_API_KEY` が設定済みであることを前提とする。

```powershell
cd C:\dev\lecture-ai-engineering-2026
```

### 2. モデルを変える

`$env:AIE_MODEL` に使いたいモデル名を入れてから、質問コマンドを実行する。

```powershell
# 今回の実験で回答を取得できたモデル
$env:AIE_MODEL = "gemini-3.5-flash-lite"
uv run python -m app.ask "AIE2026の講座の宿題にある「3レベル」とは何ですか？"

# 演習PDFに載っている別モデルへ変更する
$env:AIE_MODEL = "gemini-3.8-flash"
uv run python -m app.ask "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
```

実行時に表示される `[model]` で、選んだモデルを確認する。PDFのモデル名は資料に記載された例で、現在の利用可否を保証するものではない。今回、別モデルの試行では503で回答を取得できなかった。

この設定は同じターミナルで後から実行するコマンドにも引き継がれる。設定を消して、`app/config.py` の既定モデルに戻す場合は次を実行する。

```powershell
Remove-Item Env:AIE_MODEL -ErrorAction SilentlyContinue
```

### 3. 温度（temperature）を変える

現在の `app.ask` には `--temperature` の指定機能はない。環境変数を設定するだけでも温度は変わらないため、次のPythonコードでAPIを呼び出す。`config={"temperature": 0.2}` が温度を指定する箇所。

**次のブロック全体をPowerShellに貼り付けて実行する。** `@'` と `'@` は、間にあるPythonコードをまとめて渡すPowerShellの書き方。日本語が文字化けしないよう、渡す文字のエンコーディングも指定している。

```powershell
$env:AIE_MODEL = "gemini-3.5-flash-lite"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
@'
from google import genai
from app.config import MODEL, get_api_key

client = genai.Client(api_key=get_api_key())
question = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
temperature = 0.2

print(f"モデル: {MODEL} / 指定した温度: {temperature}")
response = client.models.generate_content(
    model=MODEL,
    contents=question,
    config={"temperature": temperature},
)
print(response.text)
usage = response.usage_metadata
if usage is not None:
    print(f"入力トークン: {usage.prompt_token_count} / 出力トークン: {usage.candidates_token_count}")
'@ | uv run python -X utf8 -
```

- 温度を変える：上の `temperature = 0.2` を、例えば `temperature = 1.0` に書き換えて、ブロックをもう一度実行する。
- 通常設定（温度未指定）と比べる：`config={"temperature": temperature},` の行を削除する。表示も `print(f"モデル: {MODEL} / 温度: 未指定")` に変更する。`temperature = 0` は「未指定」とは違う。
- モデルも変える：先頭の `$env:AIE_MODEL = "..."` を書き換える。
- 同じ条件で3回試す：同じブロックを3回実行する。各実行は独立しており、会話履歴は渡していない。

演習PDFの16ページには、temperatureの指定が無視されたり、エラーになったりする場合があると記載されている。したがって、指定が成功しても、回答の違いが温度によるものだとは断定しない。エラーや差が出なかった結果も、そのまま記録する。

### 4. Codespacesのターミナル（Bash）の場合

PDFにある `AIE_MODEL=... コマンド` はBashの書き方。PowerShellとは環境変数の設定方法が違う。CodespacesのBashなら、モデル変更は次の1行でよい（このコマンドだけに適用される）。

```bash
AIE_MODEL=gemini-3.5-flash-lite uv run python -m app.ask "LoRAとは何ですか？"
```

温度変更は、上のPowerShell例で `@'` と `'@` の間にあるPythonコードを、次の `# ここにPythonコードを貼り付ける` の行と置き換えて実行する。`PY` は行頭に置く。

```bash
AIE_MODEL=gemini-3.5-flash-lite uv run python - <<'PY'
# ここにPythonコードを貼り付ける
PY
```

モデルだけを比べるときは質問と温度の条件をそろえ、温度だけを比べるときは質問とモデルをそろえる。結果は、宿題資料の指示に沿って、使ったモデル・指定した設定・やったこと・結果を記録する。
