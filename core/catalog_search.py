"""Search the local model library and say whether a tag fits this machine."""

from __future__ import annotations

from dataclasses import dataclass

from core.local_runtime import LibraryModel, assess_fit


@dataclass
class Hardware:
    free_disk: int
    free_ram: int | None = None
    free_vram: int | None = None


@dataclass
class CatalogHit:
    name: str
    title: str
    summary: str
    quant: str
    size_bytes: int
    ram_bytes: int
    vram_bytes: int
    disk_ok: bool
    ram_ok: bool
    vram_ok: bool
    message: str


def search_models(
    models: list[LibraryModel],
    hardware: Hardware,
    *,
    text: str = "",
    quant: str = "",
    max_size: int | None = None,
    max_ram: int | None = None,
    max_vram: int | None = None,
    only_fit: bool = False,
) -> list[CatalogHit]:
    needle = text.strip().lower()
    quant_needle = quant.strip().lower()
    hits: list[CatalogHit] = []
    for model in models:
        for tag in model.tags:
            name = model.reference(tag.tag)
            blob = " ".join([name, model.name, model.summary, tag.quant, tag.tag]).lower()
            if needle and needle not in blob:
                continue
            if quant_needle and quant_needle not in tag.quant.lower():
                continue
            if max_size is not None and tag.size_bytes > max_size:
                continue
            if max_ram is not None and tag.ram_bytes > max_ram:
                continue
            if max_vram is not None and tag.vram_bytes > max_vram:
                continue
            fit = assess_fit(
                tag.size_bytes,
                hardware.free_disk,
                tag.ram_bytes,
                hardware.free_ram,
                tag.vram_bytes,
                hardware.free_vram,
            )
            if only_fit and not (fit.disk_ok and fit.ram_ok and fit.vram_ok):
                continue
            hits.append(
                CatalogHit(
                    name=name,
                    title=model.name,
                    summary=model.summary,
                    quant=tag.quant,
                    size_bytes=tag.size_bytes,
                    ram_bytes=tag.ram_bytes,
                    vram_bytes=tag.vram_bytes,
                    disk_ok=fit.disk_ok,
                    ram_ok=fit.ram_ok,
                    vram_ok=fit.vram_ok,
                    message=fit.message,
                )
            )
    return hits
