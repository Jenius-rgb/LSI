"""Build the float CNN from a model config (SPEC section 2)."""
from __future__ import annotations

import torch
from torch import nn

from model.config import KERNEL, layer_shapes


class ConvBlock(nn.Module):
    """3x3 same-padding convolution, BatchNorm, ReLU and optional 2x2 max pool."""

    def __init__(self, in_channels: int, out_channels: int, pool: bool):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, KERNEL, padding=1, bias=True)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.pool = nn.MaxPool2d(2) if pool else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.pool(self.relu(self.bn(self.conv(x))))


class SentinelNet(nn.Module):
    """Input is x/255 with no mean/std normalisation, so integer inputs are raw pixels."""

    def __init__(self, cfg: dict, n_classes: int | None = None, dropout: float = 0.0):
        super().__init__()
        shapes = layer_shapes(cfg, n_classes)
        self.blocks = nn.ModuleList(
            [ConvBlock(s.in_channels, s.out_channels, s.pool) for s in shapes if s.kind == "conv"]
        )
        self.dropout = nn.Dropout(dropout)
        fc = shapes[-1]
        self.fc = nn.Linear(fc.n_in, fc.out_channels, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x)
        return self.fc(self.dropout(torch.flatten(x, 1)))
