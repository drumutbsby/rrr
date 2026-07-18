# -*- coding: utf-8 -*-
"""
Moralite — Belge modülü: PDF/TXT/MD yükleme, metin çıkarma, diskte saklama.
Her belge `belgeler/<id>.json` olarak tutulur (sunucu yeniden başlasa da kalır).
"""
import json
import re
import uuid
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

KLASOR = Path(__file__).resolve().parent.parent / "belgeler"
KLASOR.mkdir(exist_ok=True)

DESTEKLENEN = ("pdf", "txt", "md")


def kaydet(dosya_adi: str, ham: bytes) -> dict:
    """Metni çıkarır, diske yazar; meta (id/ad/sayfa/karakter) döner."""
    uzanti = dosya_adi.lower().rsplit(".", 1)[-1] if "." in dosya_adi else ""
    if uzanti not in DESTEKLENEN:
        raise ValueError(f"desteklenmeyen tür: .{uzanti} (PDF/TXT/MD yükleyin)")

    if uzanti == "pdf":
        okuyucu = PdfReader(BytesIO(ham))
        sayfalar = [(s.extract_text() or "") for s in okuyucu.pages]
        metin = "\n\n".join(
            f"[Sayfa {i + 1}]\n{t}" for i, t in enumerate(sayfalar) if t.strip()
        )
        sayfa = len(sayfalar)
    else:
        metin = ham.decode("utf-8", errors="replace")
        sayfa = max(1, round(len(metin) / 2400))  # ~2400 karakter ≈ 1 sayfa

    metin = metin.strip()
    if not metin:
        raise ValueError("belgeden metin çıkarılamadı (taranmış PDF olabilir)")

    bid = uuid.uuid4().hex[:12]
    veri = {"id": bid, "ad": dosya_adi, "sayfa": sayfa,
            "karakter": len(metin), "metin": metin}
    (KLASOR / f"{bid}.json").write_text(
        json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    return {k: veri[k] for k in ("id", "ad", "sayfa", "karakter")}


def getir(bid: str) -> dict | None:
    """Belgeyi diskten okur; yoksa None."""
    guvenli = re.sub(r"[^a-f0-9]", "", str(bid))[:12]
    yol = KLASOR / f"{guvenli}.json"
    if not guvenli or not yol.exists():
        return None
    return json.loads(yol.read_text(encoding="utf-8"))
