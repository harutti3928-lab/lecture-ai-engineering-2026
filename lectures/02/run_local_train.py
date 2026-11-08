"""Run the local notebook, changing at most one training setting per run."""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
from IPython.core.interactiveshell import InteractiveShell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    if args.lora_r < 1 or not math.isfinite(args.lr) or args.lr <= 0:
        parser.error("--lora-r and --lr must be positive and finite")
    changes = []
    if args.epochs != 20:
        changes.append(f"epochs{args.epochs}")
    if args.lora_r != 16:
        changes.append(f"lora_r{args.lora_r}")
    if args.lr != 2e-4:
        changes.append(f"lr{args.lr:g}")
    if len(changes) > 1:
        parser.error("Change only one training setting per comparison")
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    baseline = root / "lectures/02/local_runs/baseline"
    work = baseline if not changes else baseline.parent / changes[0]
    work.mkdir(parents=True, exist_ok=True)
    if (work / "result.json").exists() or (work / "adapter").exists():
        raise RuntimeError("Training outputs already exist; preserve them before rerunning.")
    before = json.loads((baseline / "eval_before.json").read_text(encoding="utf-8"))
    prior = json.loads((baseline / "local_before_run.json").read_text(encoding="utf-8"))
    cells = json.loads((root / "lectures/02/lora_format_tuning.ipynb").read_text(encoding="utf-8"))["cells"]
    shell = InteractiveShell.instance()
    shell.user_ns["display"] = lambda value: print(value.to_string(index=False))
    report = {"started_at": datetime.now().astimezone().isoformat(), "status": "running", "cells": {}}
    started = time.perf_counter()
    try:
        for index in [2, 3, 5, 7, 9, 10, 12, 15, 17, 19]:
            print(f"Starting cell {index}", flush=True)
            code = "".join(cells[index]["source"])
            if index == 10:
                # Define scoring functions without overwriting the previous evaluation.
                expected = dict(prior["config"], num_train_epochs=args.epochs,
                                lora_r=args.lora_r, lr=args.lr, work_dir=str(work))
                assert shell.user_ns["CONFIG"] == expected
                assert [r["question"] for r in shell.user_ns["test"]] == [r["question"] for r in before["rows"]]
                if not changes:
                    code = code.split('before_summary, before_rows = evaluate(model, "before")')[0]
                    shell.user_ns.update(before_summary=before["summary"], before_rows=before["rows"])
            torch.cuda.reset_peak_memory_stats()
            cell_start = time.perf_counter()
            result = shell.run_cell(code)
            torch.cuda.synchronize()
            report["cells"][str(index)] = {
                "seconds": round(time.perf_counter() - cell_start, 2),
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            }
            if result.error_before_exec or result.error_in_exec:
                raise result.error_before_exec or result.error_in_exec
            if index == 5:
                shell.user_ns["CONFIG"].update(num_train_epochs=args.epochs,
                                               lora_r=args.lora_r, lr=args.lr, work_dir=str(work))
                shell.user_ns["WORK"] = work
                report["config"] = dict(shell.user_ns["CONFIG"])
                print("Effective config:", json.dumps(report["config"], ensure_ascii=False), flush=True)
            if index == 12:
                trainer = shell.user_ns["trainer"]
                report["training"] = {
                    "global_step": trainer.state.global_step,
                    "epoch": trainer.state.epoch,
                    "log_history": trainer.state.log_history,
                    "batch_size": trainer.args.per_device_train_batch_size,
                    "gradient_accumulation_steps": trainer.args.gradient_accumulation_steps,
                    "gradient_checkpointing": trainer.args.gradient_checkpointing,
                    "trainable_parameters": sum(p.numel() for p in trainer.model.parameters() if p.requires_grad),
                }
        report["status"] = "success"
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        report["finished_at"] = datetime.now().astimezone().isoformat()
        (work / "local_training_run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
