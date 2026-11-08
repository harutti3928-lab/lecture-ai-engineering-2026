"""Compare closed-book glossary SFT with deterministic glossary lookup."""

import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.tools import _names, _normalize, load_glossary, search_glossary

DATA = ROOT / "lectures/02/advanced_data"
WORK = ROOT / "lectures/02/local_runs/advanced"
EXPORT = ROOT / "lectures/02/results/advanced"
CONFIG = {
    "base_model": "Qwen/Qwen3.5-0.8B",
    "revision": "2fc06364715b967f1860aea9cf38778875588b17",
    "seed": 42, "num_train_epochs": 20, "lr": 2e-4,
    "lora_r": 16, "lora_alpha": 32, "max_seq_len": 512,
    "batch_size": 4, "gradient_accumulation_steps": 2,
    "warmup_steps": 6, "max_new_tokens": 192,
    "do_sample": False, "dtype": "float32",
    "task": "Plain-text glossary definitions; no glossary context supplied to model at inference",
}


def read_jsonl(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines()]


def save(name, value):
    (EXPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def abstains(raw):
    return bool(re.search(
        r"(?:記載|掲載|登録|収録).{0,18}(?:ありません|ない|いません)|"
        r"確認が必要|確認する必要|わかりません|分かりません|不明|用語集にない", raw
    ))


def grade(case, raw):
    refused = abstains(raw)
    matched = [any(_normalize(word) in _normalize(raw) for word in group)
               for group in case["keyword_groups"]]
    ok = refused if case["expected_abstain"] else all(matched) and not refused
    return {"passed": ok, "abstained": refused, "keyword_groups_matched": matched}


def lookup(question):
    """Extract the longest visible dictionary name; never inspect evaluation labels."""
    normalized = _normalize(question)
    candidates = [(len(name), term["id"], term["term"])
                  for term in load_glossary() for name in _names(term)
                  if len(name) >= 3 and name in normalized]
    query = max(candidates)[2] if candidates else question
    output = search_glossary(query)
    try:
        hits = json.loads(output)
    except json.JSONDecodeError:
        hits = []
    if not hits:
        return "用語集に記載がないため確認が必要です。", {"query": query, "hits": []}
    return hits[0]["definition"], {"query": query, "hits": [h["term"] for h in hits]}


def evaluate(label, cases, answer):
    rows = []
    start = time.perf_counter()
    for i, case in enumerate(cases):
        t0 = time.perf_counter()
        raw, details = answer(case["question"])
        rows.append({"id": case["id"], "category": case["category"], "question": case["question"],
                     "term_id": case["term_id"], "reference": case["reference"],
                     "raw": raw, **grade(case, raw), "seconds": time.perf_counter() - t0, **details})
        print(f"{label}: {i+1}/{len(cases)} {case['id']} passed={rows[-1]['passed']}", flush=True)
    summary = {"label": label, "n": len(rows), "passed": sum(r["passed"] for r in rows),
               "accuracy": sum(r["passed"] for r in rows) / len(rows),
               "seconds": round(time.perf_counter() - start, 3), "groups": {}}
    for group in ["canonical", "paraphrase", "absent"]:
        subset = [r for r in rows if r["category"] == group]
        summary["groups"][group] = {"n": len(subset), "passed": sum(r["passed"] for r in subset),
                                    "accuracy": sum(r["passed"] for r in subset) / len(subset)}
    save(f"eval_{label}.json", {"summary": summary, "rows": rows})
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return {"summary": summary, "rows": rows}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if (WORK / "adapter").exists() or (EXPORT / "result.json").exists():
        raise RuntimeError("Advanced results already exist; preserve them before rerunning")
    WORK.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((ROOT / "data/glossary.json").read_bytes()).hexdigest() == manifest["source_sha256"]
    cases, train, valid = read_jsonl("evaluation.jsonl"), read_jsonl("train.jsonl"), read_jsonl("valid.jsonl")
    load_glossary()  # The lookup measurement uses a warm, cached local dictionary.
    retrieval = evaluate("search", cases, lookup)
    set_seed(CONFIG["seed"])
    assert torch.cuda.is_available()
    tok = AutoTokenizer.from_pretrained(CONFIG["base_model"], revision=CONFIG["revision"])
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    lengths = [len(tok.apply_chat_template(row["messages"], tokenize=True, return_dict=False))
               for row in train + valid]
    assert min(lengths) > 1
    assert max(lengths) <= CONFIG["max_seq_len"], "Do not silently truncate training examples"
    model = AutoModelForCausalLM.from_pretrained(
        CONFIG["base_model"], revision=CONFIG["revision"], dtype=torch.float32
    ).to("cuda").eval()
    model.config.use_cache = True
    report = {"started_at": datetime.now().astimezone().isoformat(), "config": CONFIG,
              "gpu": torch.cuda.get_device_name(), "python": sys.version,
              "max_training_or_valid_tokens": max(lengths), "stages": {}}

    def generate(question):
        prompt = tok.apply_chat_template([
            {"role": "system", "content": manifest["system"]},
            {"role": "user", "content": question},
        ], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = tok(prompt, return_tensors="pt").to("cuda")
        torch.cuda.synchronize()
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=CONFIG["max_new_tokens"], do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize()
        new = out[0][inputs["input_ids"].shape[1]:]
        return tok.decode(new, skip_special_tokens=True).strip(), {
            "generated_tokens": len(new), "hit_token_limit": len(new) >= CONFIG["max_new_tokens"]}

    start = time.perf_counter()
    try:
        torch.cuda.reset_peak_memory_stats()
        before = evaluate("before", cases, generate)
        report["stages"]["before"] = {"peak_allocated_bytes": torch.cuda.max_memory_allocated()}
        model.config.use_cache = False
        lora = LoraConfig(r=CONFIG["lora_r"], lora_alpha=CONFIG["lora_alpha"], lora_dropout=0.05,
                          bias="none", task_type="CAUSAL_LM",
                          target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
        args = SFTConfig(
            output_dir=str(WORK / "ckpt"), num_train_epochs=CONFIG["num_train_epochs"],
            per_device_train_batch_size=CONFIG["batch_size"], gradient_accumulation_steps=CONFIG["gradient_accumulation_steps"],
            per_device_eval_batch_size=2, learning_rate=CONFIG["lr"], lr_scheduler_type="cosine",
            warmup_steps=CONFIG["warmup_steps"], logging_steps=10, save_steps=30, save_total_limit=2,
            fp16=False, bf16=False, max_length=CONFIG["max_seq_len"], packing=False,
            report_to="none", seed=CONFIG["seed"], disable_tqdm=True,
        )
        trainer = SFTTrainer(model=model, args=args, train_dataset=Dataset.from_list(train),
                             eval_dataset=Dataset.from_list(valid), peft_config=lora, processing_class=tok)
        trainer.model.print_trainable_parameters()
        torch.cuda.reset_peak_memory_stats()
        print("Starting advanced training", flush=True)
        trained = trainer.train()
        report["stages"]["training"] = {
            "metrics": trained.metrics, "log_history": trainer.state.log_history,
            "global_step": trainer.state.global_step, "epoch": trainer.state.epoch,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "gradient_checkpointing": trainer.args.gradient_checkpointing,
        }
        model = trainer.model
        model.save_pretrained(WORK / "adapter")
        report["validation"] = trainer.evaluate()
        model.config.use_cache = True
        model.eval()
        torch.cuda.reset_peak_memory_stats()
        after = evaluate("after", cases, generate)
        report["stages"]["after"] = {"peak_allocated_bytes": torch.cuda.max_memory_allocated()}
        result = {"config": CONFIG, "data_manifest": manifest,
                  "before": before["summary"], "after": after["summary"], "search": retrieval["summary"],
                  "executed_training_myself": True,
                  "regressed": [b["id"] for b,a in zip(before["rows"], after["rows"]) if b["passed"] and not a["passed"]],
                  "improved": [b["id"] for b,a in zip(before["rows"], after["rows"]) if not b["passed"] and a["passed"]],
                  "metric": "Known: all keyword groups and no abstention. Absent: explicit abstention. Not full semantic correctness.",
                  "search_method": "Longest visible dictionary name, existing search_glossary, first definition; no LLM, no oracle term IDs, warm cache."}
        save("result.json", result)
        report["status"] = "success"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["elapsed_seconds"] = time.perf_counter() - start
        report["finished_at"] = datetime.now().astimezone().isoformat()
        save("local_run.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
