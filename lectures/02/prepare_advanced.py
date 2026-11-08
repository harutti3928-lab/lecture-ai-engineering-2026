"""Build the advanced homework data using the official Q&A generator."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "lectures/02/advanced_data"
SYSTEM = (
    "あなたはAIE2026の用語説明係です。AIE2026の用語集に沿って日本語で説明してください。"
    "用語集に記載がない場合は「用語集に記載がないため確認が必要です」と答えてください。"
)

# Each group is an OR of accepted phrases; all groups must be satisfied.
# These criteria are fixed before training and also checked against the source definition.
CASES = [
    ("lora", "Low-Rank Adaptationの仕組みを教えてください。",
     [["固定", "更新しない"], ["小さな行列", "低ランク", "2つの行列", "二つの行列"], ["学習"]]),
    ("qlora", "元の重みを4ビットで保持し、小さい追加行列だけを学習する方式は何をするものですか。",
     [["4ビット", "4bit", "4-bit"], ["メモリ"], ["LoRA"]]),
    ("rate-limit", "一定時間にAPIへ送れる要求数の上限と、それを超えたときの挙動を説明してください。",
     [["リクエスト", "要求", "トークン"], ["上限", "制限"], ["429"]]),
    ("api-key", "APIを呼び出す利用者を識別する秘密の文字列は、どう管理するものですか。",
     [["秘密", "機密"], ["文字列", "キー"], ["環境変数", "secret", "書かない", "コミットしない"]]),
    ("context-window", "一度の呼び出しで扱える入力と出力の合計量には、どのような制約がありますか。",
     [["入力"], ["出力"], ["トークン"], ["上限", "限界", "制限"]]),
    ("homework-levels", "AIE2026で基礎・実装・発展のうちいくつ取り組めばよいのか、段階の構成も説明してください。",
     [["基礎"], ["実装"], ["発展"], ["どれか1つ", "どれか一つ", "いずれか1つ", "いずれか一つ", "1つ", "一つ"]]),
    ("answer-md", "AIE2026の解答ファイルの置き場所と、提出方法を教えてください。",
     [["lectures/NN/answer.md", "lectures/", "answer.md"], ["fork"], ["PR", "プルリクエスト"]]),
    ("lec-start-tag", "講座の開始タグは何のためにあり、前の回が終わっていない場合にどう役立ちますか。",
     [["演習開始", "開始時点", "開始時"], ["タグ", "tag"], ["ブランチ", "branch"]]),
    ("default-model", "AIE2026のデフォルトモデルと、それを切り替える方法を説明してください。",
     [["gemini-3.5-flash-lite"], ["AIE_MODEL"]]),
    ("temperature", "温度パラメータを低くしたときと高くしたときの違いは何ですか。",
     [["ランダム", "確率", "多様"], ["低"], ["高"]]),
]
ABSENT = ["DPO", "PPO", "RLAIF", "Mixture of Experts", "ベクトルデータベース", "修了証発行手数料"]


def normalize(text):
    return "".join(text.casefold().split())


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    if DATA.exists():
        raise RuntimeError("advanced_data already exists; preserve it before rebuilding")
    source = ROOT / "data/glossary.json"
    generator = ROOT / "scripts/make_sft_dataset.py"
    glossary = json.loads(source.read_text(encoding="utf-8"))
    terms = glossary["terms"]
    by_id = {t["id"]: t for t in terms}
    output = subprocess.run(
        [sys.executable, str(generator)], cwd=ROOT, capture_output=True, check=True,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    ).stdout
    raw = [json.loads(line) for line in output.decode("utf-8").splitlines()]
    assert len(raw) == 2 * len(terms)
    train, valid = [], []
    for i, term in enumerate(terms):
        for offset, bucket in [(0, train), (1, valid)]:
            row = raw[2 * i + offset]
            assert row["messages"][-1]["content"] == term["definition"]
            bucket.append({"messages": [{"role": "system", "content": SYSTEM}] + row["messages"]})

    evaluation = []
    for term_id, paraphrase, groups in CASES:
        term = by_id[term_id]
        assert all(any(normalize(word) in normalize(term["definition"]) for word in group) for group in groups), term_id
        for category, question in [
            ("canonical", f"{term['term']}の意味を、AIE2026の用語集に沿って教えてください。"),
            ("paraphrase", paraphrase),
        ]:
            evaluation.append({"id": f"{category}-{term_id}", "category": category,
                               "question": question, "term_id": term_id,
                               "reference": term["definition"], "keyword_groups": groups,
                               "expected_abstain": False})
    names = {normalize(n) for t in terms for n in [t["term"], t["id"], *t["aliases"]]}
    for i, name in enumerate(ABSENT):
        assert normalize(name) not in names
        evaluation.append({"id": f"absent-{i}", "category": "absent",
                           "question": f"AIE2026の用語集でいう「{name}」を説明してください。",
                           "term_id": None, "reference": "用語集に記載がないため確認が必要です。",
                           "keyword_groups": [], "expected_abstain": True})
    training_questions = {normalize(r["messages"][-2]["content"]) for r in train + valid}
    test_questions = [normalize(r["question"]) for r in evaluation]
    assert len(set(test_questions)) == len(test_questions)
    assert not set(test_questions) & training_questions

    DATA.mkdir(parents=True)
    (DATA / "glossary_sft.jsonl").write_bytes(output)
    (DATA / "glossary_snapshot.json").write_bytes(source.read_bytes())
    write_jsonl(DATA / "train.jsonl", train)
    write_jsonl(DATA / "valid.jsonl", valid)
    write_jsonl(DATA / "evaluation.jsonl", evaluation)
    manifest = {
        "source": "data/glossary.json", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_version": glossary["version"],
        "generator": "scripts/make_sft_dataset.py",
        "generator_sha256": hashlib.sha256(generator.read_bytes()).hexdigest(),
        "source_terms": len(terms), "generated_qa": len(raw), "train": len(train), "valid": len(valid),
        "evaluation": {category: sum(e["category"] == category for e in evaluation)
                       for category in ["canonical", "paraphrase", "absent"]},
        "system": SYSTEM,
        "split": "First official template per term -> train; second -> valid. Independent test questions.",
        "scope": "Known concepts appear in training. Test question wording is held out; concepts are not held out.",
        "absent_training_examples": 0,
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
