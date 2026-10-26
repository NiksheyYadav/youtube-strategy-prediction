"""Detect the machine's capabilities and choose a local model that fits it.

Why: the same project runs on a CPU-only laptop and on a laptop with an 8 GB NVIDIA GPU.  A 7B model is
comfortable on the GPU but far too slow on a CPU, so the app picks the best *installed* model whose size and
speed class suit the hardware.  Nothing is downloaded automatically; if nothing suitable is installed the app
says which model to pull.  Size figures are approximate 4-bit (Q4) download sizes.
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProfile:
    ram_gb: float
    cpu_threads: int
    gpu_name: str | None = None
    gpu_vram_gb: float | None = None

    @property
    def has_cuda_gpu(self) -> bool:
        return self.gpu_vram_gb is not None and self.gpu_vram_gb >= 3.5

    @property
    def tier(self) -> str:
        if self.has_cuda_gpu:
            return f"gpu-{int(self.gpu_vram_gb)}gb"
        return "cpu-16gb+" if self.ram_gb >= 12 else "cpu-8gb" if self.ram_gb >= 6 else "minimal"

    def describe(self) -> str:
        gpu = f"{self.gpu_name} ({self.gpu_vram_gb:.0f} GB VRAM)" if self.gpu_name and self.gpu_vram_gb else "no NVIDIA GPU"
        return f"{self.ram_gb:.0f} GB RAM, {self.cpu_threads} threads, {gpu}"


@dataclass(frozen=True)
class CatalogModel:
    prefix: str      # matched against installed model names, case-insensitive
    params_b: float
    size_gb: float   # approximate Q4 size


# Ordered best-first for structured-JSON writing tasks.
CATALOG: tuple[CatalogModel, ...] = (
    CatalogModel("qwen2.5:7b", 7.6, 4.7), CatalogModel("llama3.1:8b", 8.0, 4.9), CatalogModel("gemma2:9b", 9.2, 5.4),
    CatalogModel("qwen2.5:3b", 3.1, 1.9), CatalogModel("llama3.2:3b", 3.2, 2.0), CatalogModel("phi3.5", 3.8, 2.2),
    CatalogModel("gemma2:2b", 2.6, 1.6), CatalogModel("qwen2.5:1.5b", 1.5, 1.0), CatalogModel("llama3.2:1b", 1.2, 0.8),
)
CPU_MAX_PARAMS_B = 4.0   # CPU-only, 12 GB+ RAM: above this generation is too slow for an interactive button
CPU_MAX_PARAMS_SMALL_B = 2.0  # CPU-only with 6-12 GB RAM (typically fewer cores)
GPU_VRAM_FRACTION = 0.85  # leave room for the KV cache and the display
CPU_RAM_FRACTION = 0.35


def allowed_models(profile: DeviceProfile) -> list[CatalogModel]:
    if profile.has_cuda_gpu:
        return [m for m in CATALOG if m.size_gb <= profile.gpu_vram_gb * GPU_VRAM_FRACTION]
    if profile.ram_gb < 6:
        return []
    cap = CPU_MAX_PARAMS_B if profile.ram_gb >= 12 else CPU_MAX_PARAMS_SMALL_B
    return [m for m in CATALOG if m.params_b <= cap and m.size_gb <= profile.ram_gb * CPU_RAM_FRACTION]


@dataclass(frozen=True)
class ModelChoice:
    name: str | None
    reason: str
    pull_hint: str | None = None


def select_model(profile: DeviceProfile, installed: list[str], override: str | None = None) -> ModelChoice:
    """Best installed model that suits the hardware (an explicit override always wins)."""
    if override:
        return ModelChoice(override, "chosen explicitly with LLM_MODEL")
    allowed = allowed_models(profile)
    if not allowed:
        return ModelChoice(None, f"this device ({profile.describe()}) is too small for a local model; using rule-based advice")
    lowered = [name.lower() for name in installed]
    for model in allowed:
        for original, name in zip(installed, lowered):
            if name.startswith(model.prefix):
                return ModelChoice(original, f"best installed model for {profile.tier}")
    best = allowed[0]
    return ModelChoice(None, f"no suitable model is installed for {profile.tier}", pull_hint=f"ollama pull {best.prefix}")


# --------------------------------------------------------------------------- #
# Detection (never raises: unknown values degrade to "no GPU" / conservative RAM)
# --------------------------------------------------------------------------- #
def parse_cgroup_limit(text: str) -> float | None:
    """Container memory limit in GB from a cgroup file's text ('max' or absurdly large = unlimited)."""
    try:
        value = int(text.strip())
    except ValueError:
        return None
    return value / 1024**3 if 0 < value < 1 << 50 else None


def _container_limit_gb() -> float | None:
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(path, encoding="utf-8") as handle:
                limit = parse_cgroup_limit(handle.read())
            if limit:
                return limit
        except OSError:
            continue
    return None


def _ram_gb() -> float:
    host = _host_ram_gb()
    limit = _container_limit_gb()
    return min(host, limit) if limit else host


def _host_ram_gb() -> float:
    try:
        if platform.system() == "Windows":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong),
                            ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong), ("ext", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # type: ignore[attr-defined]
            return status.total / 1024**3
        if platform.system() == "Darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3).stdout) / 1024**3
        with open("/proc/meminfo", encoding="utf-8") as handle:
            return int(handle.readline().split()[1]) / 1024**2
    except Exception:  # noqa: BLE001 - detection must never break the app
        return 4.0


def parse_nvidia_smi(output: str) -> tuple[str, float] | None:
    """Parse `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits`; returns the largest GPU."""
    best: tuple[str, float] | None = None
    for line in output.strip().splitlines():
        name, _, memory = line.rpartition(",")
        try:
            vram = float(memory.strip()) / 1024  # MiB -> GiB
        except ValueError:
            continue
        if best is None or vram > best[1]:
            best = (name.strip(), vram)
    return best


def _nvidia_gpu() -> tuple[str, float] | None:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=5)
        return parse_nvidia_smi(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def detect_device() -> DeviceProfile:
    gpu = _nvidia_gpu()
    return DeviceProfile(ram_gb=_ram_gb(), cpu_threads=os.cpu_count() or 1,
                         gpu_name=gpu[0] if gpu else None, gpu_vram_gb=gpu[1] if gpu else None)
