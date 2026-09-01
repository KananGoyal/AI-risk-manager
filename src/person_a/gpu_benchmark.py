"""
gpu_benchmark.py - CPU (Pandas) vs GPU (cuDF) benchmark for data processing.

Scales the clean dataset incrementally (150K -> 1.5M -> test memory headroom
before attempting 15M) and measures runtime for typical feature-engineering
operations.

If the GPU runs out of memory at a given scale, the script caps the benchmark
at whatever size completed successfully and documents the cap in the chart.

IMPORTANT: This script is designed to run inside WSL2 Ubuntu with a local
NVIDIA GPU (compute capability 7.0+) and RAPIDS installed via conda/miniforge.
It will NOT work on Windows natively or in Google Colab.

Usage (inside WSL2 with rapids-env activated):
    python -m src.person_a.gpu_benchmark
"""

import os
import sys
import time
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for WSL2 / headless
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# -- Project root ------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

CLEAN_CSV = os.path.join(_PROJECT_ROOT, "data", "clean_data.csv")
CHART_PATH = os.path.join(_PROJECT_ROOT, "data", "cpu_vs_gpu_benchmark.png")

# ---------------------------------------------------------------------
# GPU memory & cuDF availability check
# ---------------------------------------------------------------------
CUDF_AVAILABLE = False
GPU_MEM_MB = 0

try:
    import cudf  # noqa: F401
    CUDF_AVAILABLE = True
    # Try to read GPU memory via nvidia-smi or pynvml
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        GPU_MEM_MB = info.total // (1024 * 1024)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu_name, bytes):
            gpu_name = gpu_name.decode()
        pynvml.nvmlShutdown()
        print(f"[benchmark] GPU detected: {gpu_name} ({GPU_MEM_MB:,} MB VRAM)", flush=True)
    except Exception:
        # Fallback: assume 8GB if we can't query
        GPU_MEM_MB = 8192
        print(f"[benchmark] cuDF available but couldn't query VRAM. Assuming {GPU_MEM_MB} MB.", flush=True)
except ImportError:
    print("[benchmark] [WARN]  cuDF not available. Running CPU-only benchmark.", flush=True)
    print("[benchmark]    Install RAPIDS via conda in WSL2 for GPU benchmarks.", flush=True)


# ---------------------------------------------------------------------
# Benchmark workload: typical feature-engineering operations
# ---------------------------------------------------------------------
def run_workload_pandas(df: pd.DataFrame) -> None:
    """Simulate typical feature-engineering operations using Pandas (CPU)."""
    # 1. Compute debt-to-income ratio (bounded)
    df["dti_ratio"] = df["debt_ratio"] * df["income"]
    # 2. Binning income into brackets
    df["income_bracket"] = pd.cut(df["income"], bins=10, labels=False)
    # 3. Group-by aggregation: mean delinquencies per income bracket
    _ = df.groupby("income_bracket")["delinquencies"].mean()
    # 4. Sort by risk-relevant column
    _ = df.sort_values("debt_ratio", ascending=False)
    # 5. Rolling / cumulative sum (simulate sequential scan)
    _ = df["income"].cumsum()


def run_workload_cudf(gdf) -> None:
    """Same workload using cuDF (GPU)."""
    import cudf as _cudf  # noqa: F811
    # 1. Compute debt-to-income
    gdf["dti_ratio"] = gdf["debt_ratio"] * gdf["income"]
    # 2. Binning income
    gdf["income_bracket"] = _cudf.cut(gdf["income"], bins=10, labels=False)
    # 3. Group-by aggregation
    _ = gdf.groupby("income_bracket")["delinquencies"].mean()
    # 4. Sort
    _ = gdf.sort_values("debt_ratio", ascending=False)
    # 5. Cumulative sum
    _ = gdf["income"].cumsum()


# ---------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------
def scale_up(df: pd.DataFrame, target_rows: int, seed: int = 42) -> pd.DataFrame:
    """
    Repeat the base dataframe to reach `target_rows`, adding small
    random noise to numeric columns so it's not a trivial duplicate.
    """
    rng = np.random.default_rng(seed)
    repeats = (target_rows // len(df)) + 1
    scaled = pd.concat([df] * repeats, ignore_index=True).head(target_rows)
    # Add +-5% noise to income and debt_ratio
    if "income" in scaled.columns:
        noise = rng.uniform(0.95, 1.05, size=len(scaled))
        scaled["income"] = scaled["income"] * noise
    if "debt_ratio" in scaled.columns:
        noise = rng.uniform(0.95, 1.05, size=len(scaled))
        scaled["debt_ratio"] = scaled["debt_ratio"] * noise
    return scaled


# ---------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------
def benchmark_pandas(df: pd.DataFrame) -> float:
    """Time the Pandas workload. Returns seconds."""
    df_copy = df.copy()
    start = time.perf_counter()
    run_workload_pandas(df_copy)
    return time.perf_counter() - start


def benchmark_cudf(df: pd.DataFrame) -> float | None:
    """
    Time the cuDF workload. Returns seconds, or None if OOM / not available.
    """
    if not CUDF_AVAILABLE:
        return None
    import cudf as _cudf  # noqa: F811
    try:
        gdf = _cudf.from_pandas(df)
        # Warm-up pass (first transfer is slower)
        run_workload_cudf(gdf.copy())
        # Timed pass
        start = time.perf_counter()
        run_workload_cudf(gdf.copy())
        elapsed = time.perf_counter() - start
        del gdf
        return elapsed
    except Exception as e:
        print(f"[benchmark] [WARN]  cuDF failed: {e}")
        return None


def estimate_max_rows(base_rows: int, base_mem_mb: float, gpu_mem_mb: int) -> int:
    """
    Estimate the max row count that fits in GPU memory, reserving 30% headroom.
    base_mem_mb is a rough estimate of how much VRAM the base dataset uses.
    """
    usable_mb = gpu_mem_mb * 0.70  # keep 30% headroom
    if base_mem_mb <= 0:
        return 15_000_000  # fallback: assume it fits
    max_rows = int((usable_mb / base_mem_mb) * base_rows)
    return max_rows


def main():
    if not os.path.exists(CLEAN_CSV):
        print(f"[benchmark] [WARN]  Clean data not found at {CLEAN_CSV}", flush=True)
        print("[benchmark]    Run clean_data.py first.", flush=True)
        sys.exit(1)

    base_df = pd.read_csv(CLEAN_CSV)
    base_rows = len(base_df)
    base_mem_mb = base_df.memory_usage(deep=True).sum() / (1024 * 1024)
    print(f"[benchmark] Base dataset: {base_rows:,} rows, ~{base_mem_mb:.1f} MB in-memory", flush=True)

    # -- Define benchmark scales ---------------------------------------
    # Start with the intended scales, then cap based on GPU memory
    intended_scales = [base_rows, 1_500_000, 15_000_000]

    if CUDF_AVAILABLE and GPU_MEM_MB > 0:
        max_rows = estimate_max_rows(base_rows, base_mem_mb, GPU_MEM_MB)
        print(f"[benchmark] Estimated max GPU rows (with 30% headroom): {max_rows:,}", flush=True)
        # Cap the largest scale
        capped_scales = []
        for s in intended_scales:
            if s <= max_rows:
                capped_scales.append(s)
            else:
                # Use the max that fits, but only if it's larger than what we have
                if not capped_scales or max_rows > capped_scales[-1]:
                    capped_scales.append(max_rows)
                break
        scales = capped_scales
    else:
        scales = intended_scales

    print(f"[benchmark] Benchmark scales: {[f'{s:,}' for s in scales]}", flush=True)

    # -- Run benchmarks ------------------------------------------------
    results = []
    actual_max_gpu_scale = 0

    for scale in scales:
        print(f"\n{'='*60}", flush=True)
        print(f"  Scale: {scale:,} rows", flush=True)
        print(f"{'='*60}", flush=True)

        df_scaled = scale_up(base_df, scale)

        # CPU (Pandas)
        cpu_time = benchmark_pandas(df_scaled)
        print(f"  CPU (Pandas):  {cpu_time:.3f}s", flush=True)

        # GPU (cuDF)
        gpu_time = benchmark_cudf(df_scaled)
        if gpu_time is not None:
            speedup = cpu_time / gpu_time if gpu_time > 0 else float("inf")
            print(f"  GPU (cuDF):    {gpu_time:.3f}s  ({speedup:.1f}x speedup)", flush=True)
            actual_max_gpu_scale = scale
        else:
            print(f"  GPU (cuDF):    SKIPPED (OOM or not available)", flush=True)

        results.append({
            "rows": scale,
            "cpu_seconds": cpu_time,
            "gpu_seconds": gpu_time,
        })

        del df_scaled

    # -- Generate chart ------------------------------------------------
    generate_chart(results, actual_max_gpu_scale)
    print(f"\n[benchmark] [OK] Benchmark complete. Chart saved to {CHART_PATH}", flush=True)


def generate_chart(results: list[dict], actual_max_gpu_scale: int):
    """Generate a grouped bar chart comparing CPU vs GPU times."""
    fig, ax = plt.subplots(figsize=(12, 7))

    labels = [f"{r['rows']:,}" for r in results]
    cpu_times = [r["cpu_seconds"] for r in results]
    gpu_times = [r["gpu_seconds"] if r["gpu_seconds"] is not None else 0 for r in results]

    x = np.arange(len(labels))
    width = 0.35

    bars_cpu = ax.bar(x - width / 2, cpu_times, width, label="CPU (Pandas)",
                      color="#3b82f6", edgecolor="white", linewidth=0.5)
    bars_gpu = ax.bar(x + width / 2, gpu_times, width, label="GPU (cuDF / RAPIDS)",
                      color="#10b981", edgecolor="white", linewidth=0.5)

    # Annotate bars with times
    for bar, t in zip(bars_cpu, cpu_times):
        ax.annotate(f"{t:.2f}s", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    for bar, t, r in zip(bars_gpu, gpu_times, results):
        if r["gpu_seconds"] is not None:
            speedup = r["cpu_seconds"] / r["gpu_seconds"] if r["gpu_seconds"] > 0 else 0
            ax.annotate(f"{t:.2f}s\n({speedup:.1f}x)",
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
        else:
            ax.annotate("N/A",
                        xy=(bar.get_x() + bar.get_width() / 2, 0.01),
                        xytext=(0, 5), textcoords="offset points", ha="center",
                        fontsize=9, color="gray")

    ax.set_xlabel("Dataset Size (rows)", fontsize=12)
    ax.set_ylabel("Execution Time (seconds)", fontsize=12)

    # Build title with actual cap info
    cap_note = ""
    if actual_max_gpu_scale > 0 and actual_max_gpu_scale < 15_000_000:
        cap_note = f"\n(GPU benchmark capped at {actual_max_gpu_scale:,} rows due to VRAM limits)"
    ax.set_title(
        f"CPU vs GPU: Feature Engineering Benchmark{cap_note}",
        fontsize=14, fontweight="bold"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    main()
