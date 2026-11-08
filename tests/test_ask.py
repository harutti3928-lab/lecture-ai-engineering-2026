"""実際のSDKのChatで履歴を検証する。HTTP通信は偽の生成関数に置き換える。"""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from google import genai
from google.genai import types

from app import ask


@pytest.fixture
def requests(monkeypatch):
    calls = []

    def make_client(**kwargs):
        client = genai.Client(api_key="test-key")

        def generate_content(*, model, contents, config=None):
            calls.append(deepcopy(contents))
            return types.GenerateContentResponse(
                candidates=[types.Candidate(
                    content=types.Content(
                        role="model", parts=[types.Part(text="好きな色は青ですね。")]
                    ),
                    finish_reason="STOP",
                )],
                usage_metadata=types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=10, candidates_token_count=5
                ),
            )

        monkeypatch.setattr(client.models, "generate_content", generate_content)
        return client

    monkeypatch.setattr(ask, "get_api_key", lambda: "test-key")
    # SDK自体は差し替えず、アプリが使うClientの生成先だけを変更する。
    monkeypatch.setattr(ask, "genai", SimpleNamespace(Client=make_client))
    return calls


def set_input(monkeypatch, lines):
    values = iter(lines)
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))


def test_chat_sends_previous_user_and_model_turns(requests, monkeypatch, capsys):
    set_input(monkeypatch, ["私の好きな色は青です。", "好きな色は何でしたか？", "/exit"])
    ask.chat()
    assert [message.role for message in requests[0]] == ["user"]
    assert [message.role for message in requests[1]] == ["user", "model", "user"]
    assert [message.parts[0].text for message in requests[1]] == [
        "私の好きな色は青です。", "好きな色は青ですね。", "好きな色は何でしたか？"
    ]
    assert capsys.readouterr().out.count("[トークン] 入力: 10 / 出力: 5") == 2


def test_chat_initial_question_blank_input_and_new_session(requests, monkeypatch):
    set_input(monkeypatch, ["  ", "/quit"])
    ask.chat("最初の質問")
    set_input(monkeypatch, ["新しい会話", "/exit"])
    ask.chat()
    assert len(requests) == 2
    assert len(requests[1]) == 1
    assert requests[1][0].parts[0].text == "新しい会話"


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
def test_chat_input_end_does_not_call_model(requests, monkeypatch, exception):
    def interrupted_input(prompt):
        raise exception

    monkeypatch.setattr("builtins.input", interrupted_input)
    ask.chat()
    assert requests == []


def test_single_question_stays_independent(requests):
    assert ask.ask("単発の質問") == "好きな色は青ですね。"
    assert requests == ["単発の質問"]


def test_cli_chat_uses_initial_question(monkeypatch):
    captured = []
    monkeypatch.setattr("sys.argv", ["app.ask", "--chat", "最初の質問"])
    monkeypatch.setattr(ask, "chat", captured.append)
    ask.main()
    assert captured == ["最初の質問"]
