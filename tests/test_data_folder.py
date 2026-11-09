"""M1: retraining on a folder dataset with an arbitrary number of classes."""
import argparse

import numpy as np
import pytest

from model import data


def make_folder(root, classes=("a", "b", "c"), per_class=12, seed=0):
    from PIL import Image

    rng = np.random.default_rng(seed)
    for split in ("train", "val"):
        for name in classes:
            (root / split / name).mkdir(parents=True)
            for i in range(per_class):
                pixels = rng.integers(0, 256, size=(48, 40, 3), dtype=np.uint8)
                Image.fromarray(pixels).save(root / split / name / f"{i}.png")


def test_folder_images_are_centre_cropped_to_32x32_chw(tmp_path):
    make_folder(tmp_path)
    ds = data.load_image_folder(tmp_path / "train")
    assert ds.images.shape == (36, 3, 32, 32) and ds.images.dtype == np.uint8
    assert ds.classes == ["a", "b", "c"]
    assert sorted(set(ds.labels.tolist())) == [0, 1, 2]


def test_load_dataset_folder_gives_train_and_val(tmp_path):
    make_folder(tmp_path)
    train, val = data.load_dataset("folder", str(tmp_path))
    assert len(train.images) == 36 and len(val.images) == 36
    with pytest.raises(ValueError):
        data.load_dataset("folder", None)


def test_empty_folder_is_an_error(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(ValueError):
        data.load_image_folder(tmp_path)


def test_training_runs_on_a_folder_with_other_class_count(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from model import train as train_mod
    from model.config import load_model_config

    make_folder(tmp_path, per_class=24)
    real_cfg = load_model_config("xs")
    small = {**real_cfg, "train": {**real_cfg["train"], "batch_size": 8, "val_size": 6}}
    monkeypatch.setattr(train_mod, "load_model_config", lambda name: small)
    args = argparse.Namespace(
        model="xs", dataset="folder", data_dir=str(tmp_path), n_classes=None, epochs=1, seed=1, device="cpu", threads=1,
        out="build/test_train_folder",
    )
    result = train_mod.train(args)
    assert result["n_classes"] == 3 and result["epochs"] == 1 and result["classes"] == ["a", "b", "c"]
