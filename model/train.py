"""Train the float model with a fixed seed and record checkpoint and log (SPEC section 4).

Example: python tools/run.py train --model s
Retraining for other classes: --dataset folder --data-dir <dir> --n-classes <N>
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import time

import numpy as np
import torch
from torch import nn

from model.arch import SentinelNet
from model.config import ROOT, load_model_config
from model.data import load_dataset


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def augment(images: torch.Tensor, rng: torch.Generator, pad: int = 4) -> torch.Tensor:
    """Random crop with padding and horizontal flip, vectorised over the batch."""
    n, _, h, w = images.shape
    padded = nn.functional.pad(images, (pad, pad, pad, pad), mode="constant", value=0)
    tops = torch.randint(0, 2 * pad + 1, (n,), generator=rng)
    lefts = torch.randint(0, 2 * pad + 1, (n,), generator=rng)
    rows = (torch.arange(h)[None, :] + tops[:, None])[:, None, :, None]
    cols = (torch.arange(w)[None, :] + lefts[:, None])[:, None, None, :]
    batch = torch.arange(n)[:, None, None, None]
    chan = torch.arange(images.shape[1])[None, :, None, None]
    cropped = padded[batch, chan, rows, cols]
    flip = torch.rand(n, generator=rng) < 0.5
    cropped[flip] = cropped[flip].flip(-1)
    return cropped


@torch.no_grad()
def accuracy(model: nn.Module, images: np.ndarray, labels: np.ndarray, device: torch.device, batch: int = 512) -> float:
    model.eval()
    correct = 0
    for i in range(0, len(images), batch):
        x = torch.from_numpy(images[i : i + batch]).float().div(255).to(device)
        y = torch.from_numpy(labels[i : i + batch]).to(device)
        correct += (model(x).argmax(1) == y).sum().item()
    return correct / len(images)


def train(args: argparse.Namespace) -> dict:
    cfg = load_model_config(args.model)
    args.dataset = args.dataset or cfg.get("dataset", "cifar10")
    tcfg = cfg["train"]
    seed = args.seed if args.seed is not None else tcfg["seed"]
    epochs = args.epochs if args.epochs is not None else tcfg["epochs"]
    seed_everything(seed)
    if args.threads:
        torch.set_num_threads(args.threads)
    device = torch.device("cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu")

    train_set, test_set = load_dataset(args.dataset, args.data_dir)
    n_classes = args.n_classes or len(train_set.classes)

    split_rng = np.random.default_rng(seed)
    perm = split_rng.permutation(len(train_set.images))
    val_size = min(tcfg["val_size"], len(perm) // 10)
    val_idx, train_idx = perm[:val_size], perm[val_size:]
    x_train = torch.from_numpy(train_set.images[train_idx])
    y_train = torch.from_numpy(train_set.labels[train_idx])

    model = SentinelNet(cfg, n_classes, tcfg["dropout"]).to(device)
    decay, no_decay = [], []
    for name, p in model.named_parameters():
        (no_decay if "bn" in name or name.endswith("bias") else decay).append(p)
    opt = torch.optim.SGD(
        [{"params": decay, "weight_decay": tcfg["weight_decay"]}, {"params": no_decay, "weight_decay": 0.0}],
        lr=tcfg["lr"], momentum=tcfg["momentum"], nesterov=True,
    )
    batch_size = tcfg["batch_size"]
    steps_per_epoch = len(x_train) // batch_size
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=tcfg["lr"], total_steps=epochs * steps_per_epoch, pct_start=0.2)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)
    rng = torch.Generator().manual_seed(seed)

    out_dir = ROOT / "results" / "model" / args.model if not args.out else ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    log_rows, best_val, best_state, best_epoch = [], -1.0, None, -1
    start = time.time()
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(x_train), generator=rng)
        total_loss = 0.0
        for b in range(steps_per_epoch):
            idx = order[b * batch_size : (b + 1) * batch_size]
            x = augment(x_train[idx], rng).float().div(255).to(device)
            y = y_train[idx].to(device)
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            sched.step()
            total_loss += loss.item()
        val_acc = accuracy(model, train_set.images[val_idx], train_set.labels[val_idx], device)
        log_rows.append([epoch, total_loss / steps_per_epoch, val_acc, time.time() - start])
        if val_acc > best_val:
            best_val, best_epoch = val_acc, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch % 10 == 0 or epoch == epochs - 1:
            print(f"epoch {epoch:3d} loss {total_loss / steps_per_epoch:.4f} val {val_acc:.4f} t {time.time() - start:.0f}s", flush=True)

    model.load_state_dict(best_state)
    test_acc = accuracy(model, test_set.images, test_set.labels, device)
    with open(out_dir / "train_log.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["epoch", "train_loss", "val_acc", "elapsed_s"])
        writer.writerows(log_rows)
    torch.save({"state_dict": best_state, "n_classes": n_classes, "classes": train_set.classes, "model": args.model}, out_dir / "float.pt")
    result = {
        "label": "[SIM]",
        "model": args.model,
        "dataset": args.dataset,
        "seed": seed,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "val_acc": best_val,
        "test_acc_float": test_acc,
        "n_classes": n_classes,
        "classes": train_set.classes,
        "train_size": len(train_idx),
        "val_size": len(val_idx),
        "test_size": len(test_set.images),
        "device": str(device),
        "threads": torch.get_num_threads(),
        "torch": torch.__version__,
        "python": platform.python_version(),
        "train_cfg": tcfg,
        "elapsed_s": time.time() - start,
    }
    (out_dir / "float_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"[SIM] {args.model}: best val {best_val:.4f} (epoch {best_epoch}), test float {test_acc:.4f}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["s", "s4", "xs"])
    parser.add_argument("--dataset", default=None, choices=["cifar10", "cifar10_4", "folder"],
                        help="default: the dataset in the model config, else cifar10")
    parser.add_argument("--data-dir", default=None, help="folder dataset root with train/ and val/")
    parser.add_argument("--n-classes", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--out", default=None, help="output directory relative to the repo root")
    train(parser.parse_args())


if __name__ == "__main__":
    main()
