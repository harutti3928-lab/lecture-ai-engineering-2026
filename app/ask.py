"""第1回: 素のLLMへの質問と、履歴を保った対話。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # 履歴を保って続けて質問する
    uv run python -m app.ask --chat "LoRAとは何ですか？"

通常は会話履歴を持たない1回の呼び出し。--chat では同じセッションの履歴を送る。
どちらもツールや講座資料は渡さない。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def _print_usage(response: types.GenerateContentResponse) -> None:
    usage = response.usage_metadata
    if usage is None:
        print("[トークン] 使用量情報なし")
    else:
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        input_label = input_tokens if input_tokens is not None else "不明"
        output_label = output_tokens if output_tokens is not None else "不明"
        print(f"[トークン] 入力: {input_label} / 出力: {output_label}")


def ask(question: str) -> str:
    with genai.Client(api_key=get_api_key()) as client:
        response = client.models.generate_content(model=MODEL, contents=question)
    _print_usage(response)
    return response.text or ""


def chat(first_question: str | None = None) -> None:
    """同じSDKのChatを使い、今回の起動中だけ会話履歴を保つ。"""
    print("対話モード：終了は /exit または /quit（Ctrl+C / 入力終了でも終了）")
    with genai.Client(api_key=get_api_key()) as client:
        session = client.chats.create(model=MODEL)
        question = first_question
        while True:
            if question is None:
                try:
                    question = input("あなた> ")
                except (EOFError, KeyboardInterrupt):
                    print("\n対話を終了します。")
                    return
            question = question.strip()
            if question in {"/exit", "/quit"}:
                print("対話を終了します。")
                return
            if question:
                print(f"[質問] {question}")
                try:
                    response = session.send_message(question)
                except KeyboardInterrupt:
                    print("\n対話を終了します。")
                    return
                _print_usage(response)
                print(f"AI> {response.text or ''}\n")
            question = None


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", help="質問（通常モードでは省略時に講座固有の質問）")
    parser.add_argument("--chat", action="store_true", help="会話履歴を保つ対話モード")
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    try:
        if args.chat:
            chat(args.question)
        else:
            question = args.question if args.question is not None else DEFAULT_QUESTION
            print(f"[質問] {question}\n")
            print(ask(question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        if e.code == 404:
            print(f"モデル '{MODEL}' が見つかりません。AIE_MODEL の値を確認してください。")
            print("AIE_MODELを、利用できるモデル名に設定してください。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
