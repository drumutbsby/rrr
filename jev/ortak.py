"""Jev (TypeSafe AI) senaryoları için ortak yardımcılar.

Anahtarı bir kez buraya yaz, on senaryo da aynı ayarı kullansın.

Kurulum:  pip install typesafe-sdk
Anahtar:  Aşağıdaki API_KEY satırına yapıştır.
          (Boş bırakırsan TYPESAFE_API_KEY ortam değişkeninden okunur.)
Proxy:    Kurumsal proxy varsa PROXY satırına, örn. "http://kullanici:sifre@proxy:8080"
Model:    MODEL boşsa hesabın varsayılan modeli kullanılır.

Çalıştırma (senaryo dosyaları bu klasörü sys.path'e aldığı için kök dizinden de olur):
    python jev/01_kart_itirazi_chargeback.py
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from typesafe_sdk import (
    Question,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeRateLimitError,
)

API_KEY = ""   # <-- anahtarı buraya yapıştır: API_KEY = "ts-..."
PROXY = ""     # <-- kurumsal proxy varsa buraya, yoksa boş bırak
MODEL = ""     # <-- belirli bir model denemek istersen, örn. MODEL = "ts-1"

ZAMAN_ASIMI = 30.0


def istemci() -> TypeSafeClient:
    """Ayarları uygulanmış bir TypeSafeClient döndürür (with bloğunda kullan)."""
    if PROXY:
        os.environ["HTTPS_PROXY"] = PROXY
    return TypeSafeClient(api_key=API_KEY or None, model=MODEL or None, timeout=ZAMAN_ASIMI)


def sor(state: Any, questions: Mapping[str, Question]) -> SystemOneResponse:
    """Tek seferlik soru seti: istemciyi açar, sorar, kapatır."""
    with istemci() as client:
        return client.system_one(state=state, questions=questions)


def yazdir(yanit: SystemOneResponse, *, basliklar: bool = True) -> None:
    """Ham cevapları okunur biçimde bas: p(evet), seçim dağılımı, skor dağılımı."""
    if basliklar:
        print(f"Model: {yanit.model}")
        print("-" * 72)

    for ad, cevap in yanit.nouls.items():
        print(f"[Noul]   {ad:<26} p(evet) = {cevap.noul:.3f}  {_cubuk(cevap.noul)}")

    for ad, cevap in yanit.choices.items():
        dagilim = ", ".join(
            f"{k}={v:.2f}" for k, v in sorted(cevap.probabilities.items(), key=lambda kv: -kv[1])
        )
        print(f"[Choice] {ad:<26} secim = {cevap.choice}  (guven {cevap.confidence:.2f})  [{dagilim}]")

    for ad, cevap in yanit.scores.items():
        dagilim = ", ".join(f"{k}={v:.2f}" for k, v in sorted(cevap.probabilities.items()))
        print(f"[Score]  {ad:<26} beklenen = {cevap.score:.2f}  (guven {cevap.confidence:.2f})  [{dagilim}]")
        for seviye, aciklama in sorted(cevap.legend.items()):
            print(f"         {'':<26}   {seviye} = {aciklama}")

    u = yanit.usage
    print(f"\nKullanim: {u.input_tokens} giris / {u.output_tokens} cikis token")


def karar(satirlar: list[str]) -> None:
    """Karar bloğunu ayrı bir çerçevede bas."""
    print()
    print("=" * 72)
    for satir in satirlar:
        print(satir)
    print("=" * 72)


def _cubuk(p: float, genislik: int = 20) -> str:
    dolu = round(p * genislik)
    return "█" * dolu + "·" * (genislik - dolu)


def calistir(baslik: str, main: Callable[[], None]) -> None:
    """Senaryoyu başlıkla çalıştır ve SDK hatalarını anlaşılır mesaja çevir."""
    print(f"\n### {baslik}\n")
    try:
        main()
    except TypeSafeAuthenticationError:
        print("API anahtari reddedildi. ortak.py icindeki API_KEY dogru mu?")
    except TypeSafeRateLimitError as hata:
        print(f"Hiz siniri asildi, biraz bekleyip tekrar dene: {hata}")
    except TypeSafeAPITimeoutError as hata:
        print(f"Istek zaman asimina ugradi (ZAMAN_ASIMI={ZAMAN_ASIMI}s): {hata}")
    except TypeSafeAPIConnectionError as hata:
        print(f"api.typesafe.ai'a baglanilamadi (proxy/TLS?): {hata}")
    except TypeSafeError as hata:
        print(f"TypeSafe hatasi: {hata}")
