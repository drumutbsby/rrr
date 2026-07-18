# -*- coding: utf-8 -*-
"""
Moralite — Kalıcı bilgi tabanı: büyük belgeler parçalanır, bge-m3 ile
vektörlenir, sqlite'ta saklanır; soru zamanı kosinüs benzerliğiyle en
yakın parçalar bulunur. Ağır bağımlılık yok: sqlite + numpy yeterli.
"""
import sqlite3
import threading
from pathlib import Path

import numpy as np
import requests

VERI_KLASOR = Path(__file__).resolve().parent.parent / "veri"
VERI_KLASOR.mkdir(exist_ok=True)
VT_YOL = VERI_KLASOR / "bilgi.db"
EMBED_MODEL = "bge-m3"
PARCA_BOYU = 1200      # karakter
BINDIRME = 200         # ardışık parçalar arası örtüşme
GRUP = 12              # embedding istek grubu

_kilit = threading.Lock()


def _baglanti():
    b = sqlite3.connect(VT_YOL)
    b.execute("""CREATE TABLE IF NOT EXISTS parcalar(
        id INTEGER PRIMARY KEY, belge_id TEXT, belge_ad TEXT,
        sira INTEGER, metin TEXT, vektor BLOB)""")
    b.execute("CREATE INDEX IF NOT EXISTS ix_belge ON parcalar(belge_id)")
    return b


def _embed(ollama_url: str, metinler: list) -> list:
    r = requests.post(
        f"{ollama_url}/api/embed",
        json={"model": EMBED_MODEL, "input": metinler},
        timeout=300,
    )
    r.raise_for_status()
    return [np.asarray(v, dtype=np.float32) for v in r.json()["embeddings"]]


def parcala(metin: str) -> list:
    parcalar, i = [], 0
    while i < len(metin):
        p = metin[i: i + PARCA_BOYU].strip()
        if p:
            parcalar.append(p)
        i += PARCA_BOYU - BINDIRME
    return parcalar


def indeksli_mi(belge_id: str) -> bool:
    with _kilit, _baglanti() as b:
        return b.execute(
            "SELECT 1 FROM parcalar WHERE belge_id=? LIMIT 1", (belge_id,)
        ).fetchone() is not None


def indeksle(ollama_url: str, belge: dict) -> int:
    """Belgeyi parçalayıp vektörler; parça sayısını döner (idempotent)."""
    parcalar = parcala(belge["metin"])
    with _kilit, _baglanti() as b:
        b.execute("DELETE FROM parcalar WHERE belge_id=?", (belge["id"],))
    for bas in range(0, len(parcalar), GRUP):
        grup = parcalar[bas: bas + GRUP]
        vektorler = _embed(ollama_url, grup)
        with _kilit, _baglanti() as b:
            b.executemany(
                "INSERT INTO parcalar(belge_id, belge_ad, sira, metin, vektor) "
                "VALUES (?,?,?,?,?)",
                [(belge["id"], belge["ad"], bas + i, m, v.tobytes())
                 for i, (m, v) in enumerate(zip(grup, vektorler))],
            )
    return len(parcalar)


def ara(ollama_url: str, soru: str, belge_idler: list = None, k: int = 6) -> list:
    """Soruya en yakın k parçayı döner: [{belge_ad, sira, metin, skor}]."""
    with _kilit, _baglanti() as b:
        if belge_idler:
            yer = ",".join("?" * len(belge_idler))
            satirlar = b.execute(
                f"SELECT belge_ad, sira, metin, vektor FROM parcalar "
                f"WHERE belge_id IN ({yer})", list(belge_idler)).fetchall()
        else:
            satirlar = b.execute(
                "SELECT belge_ad, sira, metin, vektor FROM parcalar").fetchall()
    if not satirlar:
        return []
    sv = _embed(ollama_url, [soru])[0]
    M = np.vstack([np.frombuffer(s[3], dtype=np.float32) for s in satirlar])
    skorlar = (M @ sv) / (np.linalg.norm(M, axis=1) * np.linalg.norm(sv) + 1e-9)
    sirali = np.argsort(-skorlar)[:k]
    return [
        {"belge_ad": satirlar[i][0], "sira": int(satirlar[i][1]),
         "metin": satirlar[i][2], "skor": float(skorlar[i])}
        for i in sirali
    ]
