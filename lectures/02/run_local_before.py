"""Run notebook sections 0–3 unchanged and record local GPU memory usage."""

import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import torch
from IPython.core.interactiveshell import InteractiveShell


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    notebook = root / "lectures/02/lora_format_tuning.ipynb"
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    work = root / "lectures/02/local_runs/baseline"
    work.mkdir(parents=True, exist_ok=True)
    if (work / "eval_before.json").exists():
        raise RuntimeError("eval_before.json already exists; preserve it before rerunning.")

    import os

    os.chdir(root)
    assert torch.cuda.is_available(), "CUDA is required for this local check"
    torch.cuda.reset_peak_memory_stats()
    report = {
        "started_at": datetime.now().astimezone().isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(),
        "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
        "scope": "notebook sections 0–3; no training",
        "cell_seconds": {},
    }
    shell = InteractiveShell.instance()
    shell.user_ns["display"] = lambda value: print(value.to_string(index=False))
    started = time.perf_counter()
    try:
        for index in [2, 3, 5, 7, 9, 10]:
            print(f"Starting cell {index}", flush=True)
            cell_start = time.perf_counter()
            result = shell.run_cell("".join(cells[index]["source"]))
            if result.error_before_exec or result.error_in_exec:
                raise result.error_before_exec or result.error_in_exec
            torch.cuda.synchronize()
            report["cell_seconds"][str(index)] = round(time.perf_counter() - cell_start, 2)
            if index == 9:
                original_generate = shell.user_ns["generate"]
                counter = [0]

                def generate_with_progress(*args, **kwargs):
                    counter[0] += 1
                    print(f"Evaluating question {counter[0]}/21", flush=True)
                    return original_generate(*args, **kwargs)

                shell.user_ns["generate"] = generate_with_progress
        report["status"] = "success"
        report["config"] = shell.user_ns["CONFIG"]
        report["before"] = shell.user_ns["before_summary"]
        report["model_footprint_bytes"] = shell.user_ns["model"].get_memory_footprint()
    except BaseException as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        traceback.print_exc()
        raise
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        report["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        report["peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        report["finished_at"] = datetime.now().astimezone().isoformat()
        (work / "local_before_run.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
