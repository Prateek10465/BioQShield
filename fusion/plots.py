"""Figures. Matplotlib only; no display needed."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from quantum import postprocess as pp

COLORS = {"ACCEPT": "#2e8b57", "MONITOR": "#e0a100", "REJECT": "#c0392b"}


def plot_sweep(df: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for eve, g in df.groupby("eve_rate"):
        lab = "no Eve" if eve == 0 else f"Eve on {eve:.0%}"
        ax[0].errorbar(g["noise"] * 100, g["qber"] * 100, yerr=g["qber_sd"] * 100, marker="o", ms=3, capsize=2, label=lab)
        ax[1].plot(g["noise"] * 100, g["key_bits"], marker="o", ms=3, label=lab)
    ax[0].axhline(pp.QBER_ABORT_THRESHOLD * 100, color="k", ls="--", lw=1)
    ax[0].text(0.1, pp.QBER_ABORT_THRESHOLD * 100 + 0.5, "11% hard limit", fontsize=8)
    ax[0].set(xlabel="channel noise (%)", ylabel="measured QBER (%)", title="QBER = noise + what Eve disturbs")
    ax[1].axhline(pp.MIN_KEY_BITS, color="k", ls="--", lw=1)
    ax[1].text(0.1, pp.MIN_KEY_BITS + 30, "256 bits needed for AES-256", fontsize=8)
    ax[1].set(xlabel="channel noise (%)", ylabel="secret key bits per session", title="Secret key length (8192 qubits)")
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_decision_map(df: pd.DataFrame, path: str) -> None:
    noises, eves = sorted(df["noise"].unique()), sorted(df["eve_rate"].unique())
    grid = np.zeros((len(eves), len(noises)), dtype=int)
    for _, r in df.iterrows():
        i, j = eves.index(r["eve_rate"]), noises.index(r["noise"])
        grid[i, j] = int(np.argmax([r["p_accept"], r["p_monitor"], r["p_reject"]]))
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.imshow(grid, cmap=ListedColormap([COLORS["ACCEPT"], COLORS["MONITOR"], COLORS["REJECT"]]), vmin=0, vmax=2, aspect="auto", origin="lower")
    ax.set_xticks(range(len(noises)), [f"{n:.0%}" for n in noises])
    ax.set_yticks(range(len(eves)), ["none" if e == 0 else f"{e:.0%}" for e in eves])
    ax.set(xlabel="channel noise", ylabel="share of photons Eve intercepts", title="Static policy: most likely decision")
    ax.legend(handles=[Patch(color=c, label=k) for k, c in COLORS.items()], loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_policy_comparison(df: pd.DataFrame, path: str) -> None:
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(x - 0.2, df["static_flagged"] * 100, 0.4, label="static", color="#7f8c8d")
    ax.bar(x + 0.2, df["adaptive_flagged"] * 100, 0.4, label="adaptive", color="#2c6fbb")
    ax.set_xticks(x, df["scenario"], rotation=25, ha="right", fontsize=8)
    ax.set(ylabel="sessions flagged (Monitor or Reject), %", title="Flag rate by scenario: first four are benign or weak, last ones are attacks")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_classifier(metrics: dict, top: list[tuple[str, float]], path: str, title: str) -> None:
    c = metrics["confusion"]
    cm = np.array([[c["tn"], c["fp"]], [c["fn"], c["tp"]]])
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8))
    ax[0].imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax[0].text(j, i, f"{v:,}", ha="center", va="center", color="white" if v > cm.max() / 2 else "black")
    ax[0].set_xticks([0, 1], ["pred normal", "pred attack"])
    ax[0].set_yticks([0, 1], ["is normal", "is attack"])
    ax[0].set_title(f"{title}\nacc {metrics['accuracy']:.3f}  P {metrics['precision']:.3f}  R {metrics['recall']:.3f}  F1 {metrics['f1']:.3f}", fontsize=9)
    names, vals = zip(*top[::-1])
    ax[1].barh(names, vals, color="#2c6fbb")
    ax[1].set_title("Most influential features", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_integrated(df: pd.DataFrame, path: str, note: str = "") -> None:
    traffics, quantums = list(dict.fromkeys(df["traffic"])), list(dict.fromkeys(df["quantum"]))
    fig, ax = plt.subplots(figsize=(10, 1.4 + 1.1 * len(traffics)))
    ax.set_xlim(0, len(quantums))
    ax.set_ylim(0, len(traffics))
    for _, r in df.iterrows():
        i, j = traffics.index(r["traffic"]), quantums.index(r["quantum"])
        y = len(traffics) - 1 - i
        ax.add_patch(plt.Rectangle((j, y), 1, 1, color=COLORS[r["action"]], ec="white", lw=3))
        ax.text(j + 0.5, y + 0.5, f"{r['action']}\nQBER {r['qber']:.1%}\nkey {r['key_bits']} b", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    ax.set_xticks(np.arange(len(quantums)) + 0.5, quantums, fontsize=9)
    ax.set_yticks(np.arange(len(traffics)) + 0.5, [f"{t}" for t in traffics[::-1]], fontsize=9)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Network threat (rows) x quantum channel (columns) -> decision" + (f"\n{note}" if note else ""), fontsize=10, pad=34)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_timeline(df: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.3))
    x = df["session"]
    ax.plot(x, df["qber"] * 100, color="#555", lw=1, zorder=1)
    ax.scatter(x, df["qber"] * 100, c=[COLORS[a] for a in df["action"]], s=70, zorder=3, edgecolor="white")
    ax.step(x, df["accept_limit"] * 100, where="mid", color="#2e8b57", ls=":", lw=1.5, label="accept limit (adaptive)")
    ax.axhline(pp.QBER_ABORT_THRESHOLD * 100, color="k", ls="--", lw=1, label="11% hard limit")
    ax.set_ylim(0, 14)
    start = 0
    for label, g in df.groupby("phase", sort=False):
        lo, hi = g["session"].min() - 0.5, g["session"].max() + 0.5
        ax.axvspan(lo, hi, color="#2c6fbb" if start % 2 == 0 else "#999", alpha=0.07)
        ax.text((lo + hi) / 2, 13.7, f"{label}\nthreat {g['threat'].iloc[0]:.2f}", ha="center", va="top", fontsize=7.5)
        start += 1
    ax.set(xlabel="session", ylabel="QBER (%)", title="One link over time: decisions per session")
    ax.legend(handles=[Patch(color=c, label=k) for k, c in COLORS.items()] + ax.get_legend_handles_labels()[0], fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=5)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
