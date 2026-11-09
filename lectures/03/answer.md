# 第3回 解答

## 演習

### 第2回から今回の演習へのつながり

第2回の発展課題では、講座の用語集から作ったQ&AをLoRAで学習させたLLMと、LLMを使わずに用語集を検索するプログラムを比較した。LLM側は、回答時に用語集本文を渡す方式ではなく、Q&Aを学習させたモデルに質問を渡す方式だった。検索側は、プログラムが質問文から用語名や別名を拾い、`search_glossary` を呼び、見つかった定義をそのまま返す方式だった。

自分の第2回の保存済み実行結果では、同じ26問に対する採点上の合格数は、学習前のLLMが6問、学習後のLLMが11問、検索が21問だった。特に、用語集にない語・事柄を尋ねた6問では、検索はすべて「記載がないため確認が必要」と返したのに対し、学習後のLLMはすべて裏付けのない説明を返した。この実験の範囲では、用語集にないことを断定しないという点で検索が優位だった。ただし、検索も用語名を含まない言い換えには弱く、採点上の合格も意味全体の正しさを保証するものではない。

今回の演習では、検索をLLMが使えるツールとして渡し、LLMが検索の呼び出しと引数を決め、検索結果を読んで回答を組み立てる仕組みを確かめる。第2回の検索プログラムでは用語の選び方を固定の処理で決めていたが、今回はその判断にLLMを使う。なお、検索を実際に実行するのはLLMそのものではなく、呼び出しを受け取ったプログラムである。

### エージェントとハーネスの役割

講義資料では、エージェントを「モデル＋ハーネス」、演習資料では基本の動きを「モデル＋ループ＋ツール」と説明している。今回の学習支援エージェントは、LLMだけを指すのではなく、指示や検索ツールを渡し、ツールの結果を戻して回答まで進める仕組み全体を指す。

- **モデル（LLM）**：質問・指示・ツールの説明を読み、どのツールをどの引数で呼ぶかを決める。返された検索結果を読んで回答する。
- **ツール**：`app/tools.py` の `search_glossary` や `get_lecture_summary` など、実際に検索・読み出しを行う関数。
- **ハーネス**：モデルに指示・ツールの説明・実行結果などを渡し、モデルが要求したツールを実行して、その結果をモデルへ戻すプログラム側の仕組み。今回のコードでは、`app/agent.py` での設定・登録・実行と、Pydantic AIが担う呼び出しループがこれに当たる。`INSTRUCTIONS` はハーネスからモデルへ渡す指示文であり、それだけがハーネスなのではない。

つまり、「質問 → LLMが検索を依頼 → プログラムが検索を実行 → 結果をLLMに戻す → LLMが回答する」という流れを、エージェント全体として動かす。

参照：手元の「第3回 講義資料.pdf」6〜14・23ページ、「第3回 演習講義資料.pdf」7・9〜18ページ。第2回の数値と検索方式は、`lec02` ブランチの `lectures/02/answer.md`、`lectures/02/run_advanced.py`、`lectures/02/results/advanced/result.json` に記録されたもの。上記は過去の実行結果と今回の演習の目的の整理であり、以下に記す第3回の実行結果とは区別する。

### 手順① 教材を更新し、lec03ブランチを作る

公式リポジトリ（`upstream`）の更新をmainに取り込み、自分のFork（`origin`）へpushした。そのmainから`lec03`を作成してpushし、第3回の作業を始めた。手順②の実行時点では、`app/ask.py`・`app/agent.py`・`app/tools.py`は教材のコードから変更していない。

### 手順② 同じ質問をapp.askとapp.agentに投げて比較する

2026-11-09に、このPCの既存のPython 3.12.13環境から両方を実行した。質問は「AIE2026の講座の宿題にある『3レベル』とは何ですか？」、モデルは両方とも`gemini-3.5-flash-lite`。実際のコマンドは以下のとおり（質問中のかぎ括弧は両方とも同じ）。環境を再同期せず既存の`.venv`を使うため、教材の`uv run python`の代わりにPythonを直接指定した。

```powershell
.venv/Scripts/python.exe -X utf8 -m app.ask "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
.venv/Scripts/python.exe -X utf8 -m app.agent --trace "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
```

agent側は検索の実行を確認するために`--trace`を付けた。これは同じ質問に対する記録の表示であり、手順③の「LoRAとQLoRAの違いは？」の実験はまだ行っていない。両方とも正常終了した。回答全文・実行日時・コマンド・終了コードは[実行記録](results/step02_comparison.json)に保存した。

#### app.askの回答

回答冒頭の原文：

> 申し訳ありませんが、私には「AIE2026」という特定の講座やプログラムに関する詳細な内部情報やシラバスへのアクセスがありません。

その後、一般的な難易度別課題の例として「レベル1（基礎・初級 / Basic）」「レベル2（応用・中級 / Intermediate）」「レベル3（発展・上級 / Advanced または チャレンジ課題）」を説明した。最後には講座の説明ページや講師への確認を勧めた。

講座固有の情報がないことは明示しており、一般論を講座の確定情報として断定したわけではない。ただし、この講座の正式な区分「基礎・実装・発展」や、「どれか1つに取り組めば完了」という条件には答えられなかった。

#### app.agentの回答

回答本文の原文：

> AIE2026の宿題における「3レベル」とは、宿題の難易度や内容の構成を示すもので、以下の3つの段階に分かれています。
>
> 1. **基礎**：講義内容の確認を行うレベル
> 2. **実装**：自分で実際にコードを書くレベル
> 3. **発展**：調査や新たな試行を行うレベル
>
> 3つのレベルのうち、どれか1つに取り組めばその回の宿題は完了となります。なお、原則として宿題の採点は行われません。
>
> 第1回

実際のtraceでは、次の検索が1回呼ばれていた。

```text
[tool call]   search_glossary({'query': '3レベル'})
```

ツールの返り値には「宿題の3レベル」の定義が含まれ、使用量は`requests=2, tool_calls=1`だった。LLMが検索を依頼する呼び出しと、検索結果を受けて回答する呼び出しの2回である。回答は`data/glossary.json`の`homework-levels`にある区分・完了条件・原則採点しないという説明に沿っていた。末尾の「第1回」も、この用語の`lecture: 1`と対応している。

#### 比較して分かったこと

同じモデル・同じ質問でも、askは質問だけから回答し、agentは用語集を検索して講座固有の根拠を得て回答できた。ただし、両者はツールの有無に加えてモデルへの指示も異なるので、厳密に検索の有無だけを変えた比較ではない。また、各1回の観察であり、常に同じ回答や検索回数になるとは限らない。

### 補足 なぜ回答が違うのか：コードの対応

#### ask.pyは質問だけをモデルへ渡す

`app/ask.py`の`ask()`から抜粋：

```python
def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)
```

`contents=question`で質問文を渡しているが、ここでは用語集本文も検索ツールも渡していない。`search_glossary`を呼ぶ処理もない。モデルはこのコードからローカルの`data/glossary.json`を読むことができず、既に学習した知識と質問文をもとに回答する。モデルが一般にツールを使えないという意味ではなく、この呼び出しにはツールを設定していないという違いである。

#### agent.pyは指示とツールを登録する

`app/agent.py`の`INSTRUCTIONS`には次の指示が含まれる。

```text
- 用語や講座に固有のことを答える前に、必ず search_glossary で用語集を確認する。
- 用語集に見つからないことは、推測で断定せず「用語集にはない」と伝える。
- 回答の最後に、関係する回（第N回）を示す。
```

その指示でエージェントを作成し、使える関数を登録している。

```python
agent = Agent(instructions=INSTRUCTIONS)
agent.tool_plain(tools.search_glossary)
agent.tool_plain(tools.get_lecture_summary)
```

`tool_plain`によって、関数の名前・docstringの説明・引数の型がモデルへ渡すツール定義になる。「検索すること」という指示だけでなく、実際に呼べる検索関数も用意されている点がaskと異なる。

実行時には、通常モードでこの`agent`を`target`として選び、次の処理を呼ぶ。

```python
target = build_mcp_agent() if args.mcp else agent
```

```python
result = target.run_sync(args.question, model=build_model())
```

今回`--mcp`は使っていないので、直接登録した関数ツールを使っている。`run_sync`の内部ではPydantic AIがモデルへの問い合わせ、要求されたツールの実行、結果をモデルへ戻す処理を進める。コード上は1回の`run_sync`でも、内部ではLLMを複数回呼び得る。今回のtraceは、その中で`search_glossary(query='3レベル')`が実行された記録である。

#### 用語集ファイルを実際に読むのはtools.py

`app/tools.py`の読み込み部分から抜粋：

```python
@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]
```

`search_glossary()`はこの`load_glossary()`で用語を取得し、検索に一致した項目の定義や関連する回を返す。LLMがファイルを直接開くのではなく、LLMが依頼し、プログラムが検索し、Pydantic AIが結果をLLMに戻している。この受け渡しと実行ループを担う部分がハーネスであり、LLMと合わせた仕組み全体が今回のエージェントに当たる。

### 手順③ ツール呼び出しを読む

2026-11-09に、手順②と同じPython環境・モデル（`gemini-3.5-flash-lite`）で、教材の質問を`--trace`付きで実行した。指示文・ツールの説明・実装は変更していない。

```powershell
.venv/Scripts/python.exe -X utf8 -m app.agent --trace "LoRAとQLoRAの違いは？"
```

正常終了した。回答・traceの全文と実行日時・終了コードは[手順③の実行記録](results/step03_trace.json)に保存した。

#### 実際の回答

回答本文の原文：

> 講座の用語集によると、LoRAとQLoRAの違いは以下のとおりです。
>
> * **LoRA**
>   事前学習済みの重みは固定したまま、重みの更新分を2つの小さな行列（低ランク行列）の積で表し、その小さな行列だけを学習するPEFT（Parameter-Efficient Fine-Tuning）手法です。学習するパラメータが少なく、学習結果も小さなファイルで保存できます。
>
> * **QLoRA**
>   ベースモデルの重みを4ビットなどに**量子化**してメモリを大幅に節約したうえで、LoRAによるファインチューニングを行う手法です。これにより、より大きなモデルを小さなGPU環境でも扱えるようになります。
>
> 関係する回：第2回

#### traceから確認できたこと

ツール呼び出し部分の原文：

```text
[tool call]   search_glossary({'query': 'LoRA'})
[tool call]   search_glossary({'query': 'QLoRA'})
```

続いて、それぞれの`[tool return]`にLoRA・QLoRAの定義と`lecture: 2`が表示された。CLIでは各返り値の表示が先頭120文字に省略されるため、表示だけで返り値の全文を読めるわけではない。

- 使用したツール：`search_glossary`を2回。引数`query`はそれぞれ`LoRA`と`QLoRA`。
- LLMの呼び出し回数：`requests=2`。
- ツール呼び出し回数：`tool_calls=2`。
- `get_lecture_summary`は今回のtraceには出ていない。

`requests`と`tool_calls`は別の数である。今回は、最初のモデル応答に2つの検索要求が含まれ、プログラムが両方の結果を返したあと、2回目のモデル呼び出しで回答している。検索が2回だからLLMも検索ごとに呼ばれて合計3回、という流れではなかった。ただし、この表示だけから2つの検索関数が実時間で並列実行されたかまでは判断しない。

手順②は「1用語を検索、`requests=2, tool_calls=1`」、今回は「2用語を検索、`requests=2, tool_calls=2`」だった。ツール呼び出しが増えても、必ず同じ数だけモデル呼び出しが増えるわけではないと分かった。

#### コードの指示と実際の動きの対応

`app/agent.py`の`INSTRUCTIONS`には次の指示がある。

```text
- 用語や講座に固有のことを答える前に、必ず search_glossary で用語集を確認する。
- 回答の最後に、関係する回（第N回）を示す。
```

`app/tools.py`の`search_glossary`のdocstringには、次の説明がある。

```text
答える前に使うこと。query には調べたい用語を1つだけ入れる（例: "LoRA"）。
```

今回の動きはこれらの指示に沿っており、回答前に検索し、`LoRAとQLoRA`という1つの検索語にまとめず、用語ごとに検索した。回答末尾には、検索結果の`lecture: 2`に対応する「第2回」が付いた。これらは今回の観察と指示文の対応であり、どの指示がどれだけ動きに影響したかを確かめるには、宿題の基礎のように指示を1か所ずつ変更して比較する必要がある。

### 手順④ make_quizツールを作成して登録する

演習資料17ページの手順に沿って、指定した回の用語から確認問題と答えを返すツールを追加した。変更したのは[`app/tools.py`](../../app/tools.py)と[`app/agent.py`](../../app/agent.py)。この段階ではツールの作成・登録と関数の直接確認まで行い、LLMが実際に呼ぶかの確認は手順⑤で行う。

#### tools.py：用語を選び、問題と答えを返す

`app/tools.py`に`import random`を加え、次の関数を追加した。

```python
def make_quiz(lecture: int) -> str:
    """指定した回の用語から1つを選び、確認問題と答えを返す。

    「第2回の確認問題を出して」のように、復習用の問題を求められたときに使う。
    lectureには出題したい回の番号を指定する。
    """
    terms = [entry for entry in load_glossary() if entry["lecture"] == lecture]
    if not terms:
        return f"第{lecture}回の用語が用語集にないため、確認問題を作れません。"

    entry = random.choice(terms)
    return json.dumps(
        {"question": f"「{entry['term']}」の意味は？", "answer": entry["definition"]},
        ensure_ascii=False,
    )
```

- `lecture: int`は出題する回の番号、`-> str`は返り値が文字列であることを示す。
- docstringは利用者向けの説明だけではなく、LLMに渡すツールの説明になる。「復習用の問題を求められたとき」という使用場面を書いた。
- `load_glossary()`で用語集を読み、`entry["lecture"] == lecture`で指定回の用語だけを集める。
- `random.choice(terms)`で候補から1つ選ぶ。用語の選択はLLMではなく、このPython関数が行う。毎回同じ問題になるとは限らない。
- 問題文と、用語集の定義を使った答えをJSON文字列で返す。`ensure_ascii=False`で日本語をそのまま出力する。
- 用語がない場合は空の候補から選ばず、説明文を返す。第0回などの指定でも例外で落ちない。

ここで返す答えはツールからLLMに渡る情報であり、そのまま利用者へ表示する処理ではない。LLMはその結果を使って出題する。

#### agent.py：ツールを登録する

`app/agent.py`の既存ツール登録に続けて、演習のTODOを次の1行に置き換えた。

```python
agent.tool_plain(tools.make_quiz)
```

関数を書くだけではモデルから呼べないため、`tool_plain`で使えるツールに加える。`tools.make_quiz`は関数そのものを渡しており、ここで`make_quiz(2)`を実行しているわけではない。モデルが呼び出しを要求したときに、Pydantic AIが指定された引数で関数を実行する。今回、`INSTRUCTIONS`は変更していない。

#### この手順で確認したこと

2026-11-09に既存のPython環境で、APIを使わず関数を直接呼んだ。`make_quiz(2)`が返した問題は「『Hugging Face Hub』の意味は？」で、答えは用語集の該当定義だった。問題と答えの組が第2回の用語集データに一致することを確認した。

`make_quiz(0)`と`make_quiz(999)`は、それぞれ「第0回の用語が用語集にないため、確認問題を作れません。」「第999回の用語が用語集にないため、確認問題を作れません。」を返し、正常に終了した。これは関数単体の確認であり、モデルによるツール選択や登録後の一覧表示の確認ではない。

### 手順⑤ make_quizがモデルから呼ばれるか確かめる

2026-11-09に、演習資料18ページに沿って次の3つを実行した。モデルは`gemini-3.5-flash-lite`で、手順④からコードや`INSTRUCTIONS`は変更していない。全文と各コマンドの実行日時・終了コードは[手順⑤の実行記録](results/step05_verification.json)に保存した。

```powershell
.venv/Scripts/python.exe -X utf8 -m app.agent --list-tools
.venv/Scripts/python.exe -X utf8 -m app.agent --trace "第2回の内容から確認問題を1問出して"
.venv/Scripts/python.exe -X utf8 -m pytest -q
```

#### 1. モデルに渡すツール一覧

`--list-tools`はAPIを呼ばず、`TestModel`でツール定義を読み出す。`search_glossary`・`get_lecture_summary`・`make_quiz`の3個が表示された。追加したツールの表示は次のとおり。

```text
[make_quiz]
  指定した回の用語から1つを選び、確認問題と答えを返す。

  「第2回の確認問題を出して」のように、復習用の問題を求められたときに使う。
  lectureには出題したい回の番号を指定する。
  引数: {"lecture": {"type": "integer"}}
```

関数名だけでなく、docstringの説明と引数の型がモデルに渡されることを確認できた。

#### 2. 実際の出題とtrace

回答本文の原文：

> 第2回の内容から確認問題です！
>
> **問題：**
> 「LoRA」とはどのような手法でしょうか？
>
> （考えてみてくださいね。答えを知りたいときは「答えを教えて」と聞いてください！）
>
> 関係する回：第2回

呼び出しの記録：

```text
[tool call]   make_quiz({'lecture': 2})
```

ツールの返り値には`question: 「LoRA」の意味は？`と、用語集の定義を使った`answer`が含まれていた。使用量は`requests=2, tool_calls=1`で、今回は`make_quiz`だけが呼ばれた。モデルが依頼から回の番号`2`を選び、Python関数が第2回の候補からLoRAを選び、その結果を使ってモデルが出題したことが分かる。`INSTRUCTIONS`への追加指示は不要で、今回の1回ではdocstringと登録だけで目的のツールが選ばれた。

ツールが問題と答えの両方を返しても、モデルは今回、答えを回答本文には表示しなかった。ツールの返り値と、利用者に見せる最終回答が別であることも確認できた。ただし`--trace`には答えの一部も出るため、自力で解きたい場合はその表示に注意する。また、回答には「答えを教えて」と聞くよう案内があるが、現在のCLIは1回の質問で終了し、次の起動へ会話履歴を引き継がない。そのまま次のコマンドで答えを聞けることまで確認したわけではない。

#### 3. テスト

```text
15 passed in 8.22s
```

既存テストはすべて成功した。`tests/test_agent.py`では`TestModel`が登録済みツールを呼び、結果がモデルへ戻ることを確認している。追加した`make_quiz`もこの呼び出しの対象となり、ダミーの引数（`lecture=0`）で用語がない場合も落ちなかった。APIを使う実際の出題と、APIを使わない配線の確認の両方ができた。

## 宿題

### 基礎：ツールの説明文を変えて比較する

#### やったこと・比較条件

宿題資料1〜2ページに沿って、[`app/tools.py`](../../app/tools.py)の`search_glossary`のdocstringを1か所だけ変更し、同じ質問を`--trace`付きで実行した。

変更前：

```text
答える前に使うこと。query には調べたい用語を1つだけ入れる（例: "LoRA"）。
```

変更後：

```text
答える前に使うこと。query には調べたい用語をまとめて入れる（例: "LoRAとQLoRA"）。
```

2026-11-09に両条件を各1回実行した。質問は「LoRAとQLoRAの違いは？」、モデルは`gemini-3.5-flash-lite`、環境は既存のPython 3.12.13。`INSTRUCTIONS`、検索関数の処理、用語集、ツール構成（`make_quiz`を含む3個）は変えていない。新しいプロセスから起動し、会話履歴は引き継いでいない。生成設定やseedは追加指定していない。

演習③の時点では`make_quiz`が未登録だったため、その記録をそのまま比較対象にせず、現在の3ツール構成で変更前条件も取り直した。実行コマンドは両方とも同じである。

```powershell
.venv/Scripts/python.exe -X utf8 -m app.agent --trace "LoRAとQLoRAの違いは？"
```

両方とも正常終了した。回答・trace・実際のdocstring・日時・終了コードは[変更前](results/homework_basic_before.json)と[変更後](results/homework_basic_after.json)に保存した。以下の数値は今回の実行結果であり、教材に記載された例の数値ではない。

#### 結果：検索が2回から1回に変わった

変更前の呼び出し：

```text
[tool call]   search_glossary({'query': 'LoRA'})
[tool call]   search_glossary({'query': 'QLoRA'})
```

変更後の呼び出し：

```text
[tool call]   search_glossary({'query': 'LoRA QLoRA'})
```

- 変更前：`requests=2, tool_calls=2`、入力1,368トークン、出力166トークン。
- 変更後：`requests=2, tool_calls=1`、入力1,065トークン、出力193トークン。

「まとめて入れる」という説明に変えると、今回のモデルは実際に2用語を1つの引数にまとめた。ただし、docstringの例文`LoRAとQLoRA`をそのまま使ったのではなく、空白区切りの`LoRA QLoRA`を選んだ。

LLMの呼び出し回数は変わらなかった。変更前も最初のモデル応答で2つの検索を依頼していたため、どちらも「検索を依頼するモデル呼び出し → ツール実行 → 結果を読んで答えるモデル呼び出し」の2回だった。入力トークンは減ったが出力トークンは増えており、1回ずつの結果から費用や速度が常に改善するとまでは言えない。

#### 最終回答の比較

変更前の回答は、LoRAを「重みを固定し、小さな行列（アダプタ）だけを学習する手法」、QLoRAを「ベースモデルを量子化してメモリを抑えたうえでLoRAによる学習を行う手法」と説明し、「関係する回：第2回」で終わった。

変更後の回答も同じ違いを説明し、「Low-Rank Adaptation」「Quantized LoRA」という英語名や、学習パラメータ数・保存ファイルサイズの削減について説明を加え、「（第2回）」で終わった。表現や詳しさには違いがあるが、今回の観察では中心となる説明は維持された。回答全文は上記JSONに保存している。英語名などを含む文面全体を独立に採点した実験ではない。

#### なぜまとめた検索でも結果が返ったのか

`--trace`の`[tool return]`は先頭120文字で省略される。その表示だけで全文を断定せず、実験後に同じ関数を`search_glossary("LoRA QLoRA")`で直接呼んだところ、LoRAとQLoRAの両方の定義が返った。[直接確認の記録](results/homework_basic_search_check.json)に全文を保存した。これはモデル実行時の返り値全文を取得したものではなく、その後のローカル関数による確認である。

関連する処理は`app/tools.py`の次の箇所である（抜粋）。

```python
def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")
```

```python
partial = [
    e for e in glossary
    if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
]
```

`LoRA QLoRA`は正規化で`loraqlora`になり、その中に用語名`lora`と`qlora`が含まれるため、部分一致で両方が候補になった。説明文を変えたことで複数語を構造的に分解する処理が追加されたわけではなく、既存の部分一致がこの質問に対応できたということになる。検索は最大3件なので、別の用語の組み合わせや、多数の用語をまとめた場合にも適切な結果がそろうとは限らない。

#### 気づき・疑問

ツールのdocstringは単なる開発者向けコメントではなく、モデルのツール選択や引数の作り方に関係する指示である。今回、実行処理を変更せず説明文だけを変えたところ、観測された検索の回数と引数が変わった。

一方、docstringを変えても関数の能力や制限は変わらない。モデルへ渡す説明と実装の対応を確認する必要がある。また、各条件1回だけなので、変更が常に同じ効果を生むという証明ではない。複数回の再実行や別の質問でも同じ傾向かは未検証である。

現時点の`app/tools.py`には変更後のdocstringを残している。以下の発展(a)も同じ説明文を使って比較する。実装レベルは実施していない。

### 発展(a)：同じ指示とツールをGoogle ADKで組み立てる

#### やったことと目的

宿題資料3ページに沿って、エージェントを組み立てる部分をGoogle ADKで書き、`adk run`で動かした。モデルを学習し直したり、検索関数を作り直したりする課題ではなく、同じ指示と道具を別のフレームワークで使い、コードの書き方と回答を比較する課題である。

新しく作成したファイル：

- [`adk_agent/glossary_agent/agent.py`](../../adk_agent/glossary_agent/agent.py)：ADKのエージェント定義。
- [`adk_agent/glossary_agent/__init__.py`](../../adk_agent/glossary_agent/__init__.py)：`from . import agent`の1行。
- [`adk_agent/README.md`](../../adk_agent/README.md)：このPCでの起動手順と比較方法。

発展のために`app/`のファイルは変更していない。`INSTRUCTIONS`と、`search_glossary`・`get_lecture_summary`・演習で追加した`make_quiz`をそのままインポートした。指示の値とツール関数オブジェクトが元のものと一致することも、APIなしの確認で確かめた。

#### コードの書き方の違い

既存のPydantic AI版（`app/agent.py`、抜粋）：

```python
agent = Agent(instructions=INSTRUCTIONS)
agent.tool_plain(tools.search_glossary)
agent.tool_plain(tools.get_lecture_summary)
agent.tool_plain(tools.make_quiz)
```

ADK版（`adk_agent/glossary_agent/agent.py`）：

```python
from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL

root_agent = Agent(
    model=MODEL,
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
```

Pydantic AIでは`instructions=`で全体指示を渡し、`tool_plain()`で関数を登録する。ADKでは`instruction=`と`tools=[...]`をまとめて渡し、CLIが読み込む`root_agent`として定義する。モデルは教材の文字列を重複記載する代わりに`app.config.MODEL`を参照し、両版で同じ設定を使うようにした。

実行部分も、既存版では自作CLIから`target.run_sync(...)`を呼ぶのに対し、ADK版では`adk run`が実行ループを担う。どちらも、関数そのものはプログラム側で実行し、その結果をモデルに戻す。フレームワークのハーネス部分を替えても、指示とツールの実装を共有できた。

#### 実行環境・コマンド

2026-11-09にこのWindows PCで実行した。既存環境を再同期しないため、教材の`uv run --with google-adk`に`--no-sync`を追加した。ADKは一時環境へ導入し、導入後に確認したバージョン`2.14.0`を比較時の指定に固定した。`pyproject.toml`・`uv.lock`や既存の`.venv`への追加インストールは行っていない。

比較したモデルは両方`gemini-3.5-flash-lite`、Pythonは3.12.13。ADK実行環境でも`google-genai=2.31.0`、`pydantic-ai-slim=2.57.0`であることを確認した。環境変数の`GEMINI_API_KEY`をそのまま使い、キーをファイルへ保存していない。

リポジトリ直下のPowerShellで対話起動する方法：

```powershell
$env:PYTHONPATH = (Get-Location).Path
uv run --no-sync --with google-adk==2.14.0 adk run --in_memory adk_agent/glossary_agent
```

教材の`PYTHONPATH=.`はPOSIXシェルの書き方なので、PowerShellの環境変数設定に置き換えた。比較実験では、ADKの既存CLIが対応する質問引数を使い、1問ずつ新しいプロセス・セッションで実行した。例えば次のとおり。

```powershell
uv run --no-sync --with google-adk==2.14.0 adk run --in_memory --jsonl adk_agent/glossary_agent "LoRAとQLoRAの違いは？"
```

`--in_memory`はセッションのDB保存を避ける指定、`--jsonl`はCLI既存のイベント出力を記録する指定。独自の`--trace`機能や承認付きツールは追加していない。Pydantic AI側は既存の`app.agent --trace`で実行した。

#### 比較条件と結果

演習で使った3問を、それぞれ両版で1回ずつ実行した。以前の出力との比較だけで済ませず、基礎課題後の同じ指示・3ツール・用語集でPydantic AI版も取り直した。履歴を持ち越さず、生成設定やseedは追加指定していない。6回すべて正常終了した。各コマンド・日時・回答全文・traceまたはADKイベントは[比較実行記録](results/homework_advanced_adk.json)に保存し、各runの`summary`にも回答と呼び出しを整理した。

**1. 「AIE2026の講座の宿題にある『3レベル』とは何ですか？」**

両版とも`search_glossary(query="3レベル")`を1回呼び、「基礎・実装・発展」「どれか1つで完了」「原則として採点はしない」を回答した。関連回はいずれも第1回。Pydantic AI版の「ご自身の学習状況に合わせて」といった言い回しや段落構成には違いがあるが、確認した中心的な内容は一致していた。

**2. 「LoRAとQLoRAの違いは？」**

両版とも`search_glossary(query="LoRA QLoRA")`を1回呼んだ。Pydantic AI版は冒頭で「ベースモデルの重みの保持方法（ビット精度）」、ADK版は「ベースモデルの重みの量子化（精度）と、それに伴うメモリ消費量」を主な違いとして説明した。

どちらも、LoRAは重みを固定して追加した低ランク行列を学習し、QLoRAはベースモデルを量子化したうえでLoRAによる学習を行うと説明した。末尾にはどちらも第2回が付いた。今回の観察では検索方法と中心的な説明は共通だった。文章全体の正確性を自動採点した実験ではない。

**3. 「第2回の内容から確認問題を1問出して」**

両版とも`make_quiz(lecture=2)`を1回呼んだ。Pydantic AI版は「ランク（LoRAのr）」、ADK版は「PEFT」を出題した。どちらも最終回答に答え自体は表示せず、関連回として第2回を示した。

出題語が違ったのはツールの`random.choice`の返り値が異なったためであり、それをフレームワークによる問題選択の違いとは解釈できない。乱数seedは固定しておらず、同一のツール結果を渡した比較ではない。

**呼び出しの流れ**

Pydantic AI版は全3問で`requests=2, tool_calls=1`。ADK版も各問で、モデルのツール要求イベント、関数の結果イベント、モデルの最終回答イベントが順に記録され、使用量を持つモデル応答イベントは2件だった。ADK独自の指標を`requests`として記録したのではなく、イベントから同様の流れを確認した。今回`get_lecture_summary`はどちらでも呼ばれなかったため、3ツールすべてを実APIで使用した検証ではない。

#### 気づき・限界

同じ指示とPython関数を使うことで、フレームワークを替えても今回の3問では似た動きを再現できた。違いが大きかったのは、指示・ツールを渡すAPIの書き方と、CLIやイベント記録など実行部分の用意の仕方である。

ただし、同じ指示の文字列を渡しても、フレームワークが作るツール定義、メッセージの構成、既定設定などまで同一とは限らない。各問1回で、モデルの生成と出題には揺らぎがあるため、回答の表現差をすべてフレームワークの効果とは断定できない。この課題では速度・費用の優劣や、どちらが一般に高精度かまでは評価していない。

参照した公式資料：[ADK Python Quickstart](https://adk.dev/get-started/python/)、[Command Line](https://adk.dev/runtime/command-line/)。教材の課題範囲と、上記の実行結果・このPC用の環境調整は区別して記録した。
