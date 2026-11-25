"""Compute parameters, MACs and ideal cycles from a model config (SPEC 2, 5.4)."""
from __future__ import annotations

import argparse
import json

from model.config import ROOT, layer_shapes, load_model_config


def report(model: str, ks: tuple[int, ...] = (8, 16)) -> dict:
    cfg = load_model_config(model)
    shapes = layer_shapes(cfg)
    layers = [
        {
            "name": s.name,
            "kind": s.kind,
            "input": [s.in_channels, s.in_height, s.in_width],
            "output_channels": s.out_channels,
            "weights": s.weights,
            "bias": s.out_channels,
            "macs": s.macs,
            "t": s.t,
            "groups": {str(k): s.groups(k) for k in ks},
            "ideal_cycles": {str(k): s.ideal_cycles(k) for k in ks},
        }
        for s in shapes
    ]
    return {
        "model": model,
        "layers": layers,
        "total_weights": sum(s.weights for s in shapes),
        "total_bias": sum(s.out_channels for s in shapes),
        "total_macs": sum(s.macs for s in shapes),
        "ideal_cycles": {str(k): sum(s.ideal_cycles(k) for s in shapes) for k in ks},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="all", choices=["s", "s4", "xs", "all"])
    args = parser.parse_args()
    out_dir = ROOT / "results" / "model"
    out_dir.mkdir(parents=True, exist_ok=True)
    for model in ["s", "s4", "xs"] if args.model == "all" else [args.model]:
        rep = report(model)
        (out_dir / f"arch_{model}.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
        print(f"[SIM] model {model}")
        for layer in rep["layers"]:
            print(
                f"  {layer['name']:<6} weights={layer['weights']:>6} macs={layer['macs']:>8}"
                f" T={layer['t']:>4} cycles(K=8)={layer['ideal_cycles']['8']:>7}"
            )
        print(
            f"  total weights={rep['total_weights']} bias={rep['total_bias']} macs={rep['total_macs']}"
            f" cycles={rep['ideal_cycles']}"
        )


if __name__ == "__main__":
    main()
