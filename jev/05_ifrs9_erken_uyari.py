"""05 — Ticari kredi erken uyarı ve izleme grubu (IFRS 9 aşama geçişi).

Senaryo:  Aylık erken uyarı taraması. Firma hakkında sayısal sinyaller (limit kullanımı,
          çek/senet, vergi-SGK borcu) ile niteliksel sinyaller (basın haberi, KAP,
          müşteri ziyaret notu) bir arada. Amaç: kredinin 1. aşamadan 2. aşamaya
          (yakın izleme) alınıp alınmayacağına dair gerekçeli bir öneri üretmek.

Jev'e sorulan:  niteliksel metinlerin "kredi riskinde önemli artış" anlamına gelip
                gelmediği, sorunun geçici likidite mi yapısal bozulma mı olduğu.
Kodda kalan:    gecikme günü, aşama geçiş kuralı, karşılık etkisi, komite kademesi.

Ek olarak:  typed response — cevaplar `yanit.temerrut_yakin` gibi alan olarak geliyor
            (system_one(..., response_model=...)).

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 05_ifrs9_erken_uyari.py
"""

import os

from typesafe_sdk import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
)


API_KEY = ""   # <-- anahtarı buraya yapıştır: API_KEY = "ts-..."
PROXY = ""     # <-- kurumsal proxy varsa buraya, yoksa boş bırak


def anahtar() -> str | None:
    """API_KEY boşsa Colab Secrets'tan oku; o da yoksa SDK ortam değişkenine baksın."""
    if API_KEY:
        return API_KEY
    try:  # Colab: sol menü > anahtar simgesi > TYPESAFE_API_KEY
        from google.colab import userdata  # type: ignore[import-not-found]

        return userdata.get("TYPESAFE_API_KEY")
    except Exception:
        return None  # None => SDK, TYPESAFE_API_KEY ortam değişkenini kullanır


GECIKME_GUN = 24
LIMIT_KULLANIM = 0.97
BAKIYE_TL = 47_500_000.0

STATE = {
    "firma": {"unvan": "ANADOLU TEKSTIL A.S.", "sektor": "hazir_giyim_ihracat", "risk_bakiyesi_tl": BAKIYE_TL},
    "sayisal_sinyaller": {
        "nakdi_limit_kullanim_orani": LIMIT_KULLANIM,
        "en_uzun_gecikme_gun": GECIKME_GUN,
        "son_6_ay_karsiliksiz_cek_adet": 3,
        "vergi_sgk_borcu_tl": 4_900_000,
        "kredi_notu_degisimi": "1.380 -> 1.055 (6 ay)",
        "teminat_kapsama_orani": 0.62,
    },
    "niteliksel_sinyaller": [
        "Sektör haberi: firmanın en büyük Avrupa alıcısı konkordato ilan etti (basında, 12 gün önce).",
        "Firma, iki üretim vardiyasından birini süresiz durdurduğunu duyurdu.",
        "CFO istifa etti, yerine atama yapılmadı.",
        "Müşteri ziyaret notu: 'İhracat alacaklarımız donduğu için kısa vadeli sıkışıklık var, "
        "yeni alıcıyla sözleşme imzalanmak üzere, üç ayda toparlarız' dendi. Sözleşme taslağı gösterilmedi.",
        "Firma, başka bir bankadaki kredisini 24 ay vade uzatımıyla yapılandırdığını söyledi.",
    ],
}

SORULAR = {
    "temerrut_yakin": Noul(
        instructions=(
            "Taken together, the signals indicate that the borrower is unlikely to pay its credit "
            "obligations in full without the bank realising collateral or granting relief."
        ),
    ),
    "yapisal_bozulma": Noul(
        instructions="The deterioration looks structural rather than a temporary liquidity squeeze.",
        criteria={
            "true": "The borrower's business model, main market or capacity is impaired in a lasting way.",
            "false": "The problem is timing of cash flows and the underlying business is intact.",
        },
    ),
    "baska_bankada_yapilandirma": Noul(
        instructions="The borrower has restructured or extended debt with another creditor because of financial difficulty.",
    ),
    "yonetim_zayifligi": Noul(
        instructions="There are governance or management stability problems at the borrower.",
    ),
    "beyan_dogrulanabilir": Noul(
        instructions="The borrower's recovery claims are backed by verifiable evidence.",
        criteria={
            "true": "Contracts, orders or documents supporting the recovery plan were actually shown.",
            "false": "The recovery plan rests on statements only, with no document produced.",
        },
    ),
    "ana_risk": Choice(
        instructions="What is the dominant driver of risk in this file?",
        criteria={
            "alici_yogunlasmasi": "Loss or distress of a dominant buyer.",
            "sektorel_daralma": "Sector-wide contraction in demand or margins.",
            "likidite": "Cash-flow timing problems with an otherwise sound business.",
            "yonetim": "Management or governance failure.",
            "asiri_borcluluk": "Debt load too large for the business to service.",
        },
    ),
    "izleme_siddeti": Score(
        instructions="How closely should this exposure be monitored from now on?",
        criteria=[
            "Standard: no change in monitoring.",
            "Close watch: quarterly review, tighter limits, collateral review.",
            "Intensive: monthly review, no new limits, exit or restructuring plan required.",
        ],
    ),
}


class ErkenUyariYaniti(SystemOneResponse):
    """Soru adlarıyla birebir alan tanımlarsan cevaplar tip güvenli biçimde üst seviyeye çıkar."""

    temerrut_yakin: NoulAnswer
    yapisal_bozulma: NoulAnswer
    beyan_dogrulanabilir: NoulAnswer
    ana_risk: ChoiceAnswer
    izleme_siddeti: ScoreAnswer


def main() -> None:
    print("### Ticari kredi erken uyari / IFRS 9 asama onerisi\n")

    if PROXY:
        os.environ["HTTPS_PROXY"] = PROXY

    with TypeSafeClient(api_key=anahtar(), timeout=30) as client:
        yanit = client.system_one(state=STATE, questions=SORULAR, response_model=ErkenUyariYaniti)

    # Tip güvenli erişim: sözlük anahtarı yerine alan adı.
    print(f"Model: {yanit.model}")
    print(f"temerrut_yakin        p = {yanit.temerrut_yakin.noul:.3f}")
    print(f"yapisal_bozulma       p = {yanit.yapisal_bozulma.noul:.3f}")
    print(f"beyan_dogrulanabilir  p = {yanit.beyan_dogrulanabilir.noul:.3f}")
    print(f"ana_risk              {yanit.ana_risk.choice} (guven {yanit.ana_risk.confidence:.2f})")
    print(f"izleme_siddeti        {yanit.izleme_siddeti.score:.2f} (guven {yanit.izleme_siddeti.confidence:.2f})")
    for ad, cevap in yanit.nouls.items():
        if ad not in {"temerrut_yakin", "yapisal_bozulma", "beyan_dogrulanabilir"}:
            print(f"{ad:<22} p = {cevap.noul:.3f}")

    # --- IFRS 9 aşama kuralı: kantitatif tetik VEYA nitel "önemli artış" -----------------------
    kantitatif_tetik = GECIKME_GUN >= 30 or LIMIT_KULLANIM >= 1.0
    nitel_tetik = (
        yanit.temerrut_yakin.noul > 0.6
        or (yanit.yapisal_bozulma.noul > 0.6 and yanit.izleme_siddeti.score >= 1.5)
        or yanit.nouls["baska_bankada_yapilandirma"].noul > 0.7
    )
    ispatsiz_iyilesme_beyani = yanit.beyan_dogrulanabilir.noul < 0.4

    satirlar = [
        f"Risk bakiyesi: {BAKIYE_TL:,.0f} TL | Gecikme: {GECIKME_GUN} gun | "
        f"Limit kullanim: {LIMIT_KULLANIM:.0%} | Teminat kapsama: 62%",
        f"Kantitatif tetik: {'var' if kantitatif_tetik else 'yok'} | Nitel tetik: {'var' if nitel_tetik else 'yok'}",
    ]

    if yanit.temerrut_yakin.noul > 0.8 and yanit.yapisal_bozulma.noul > 0.7:
        satirlar += [
            "Oneri: 3. ASAMA degerlendirmesi (temerrut karinesi). Tahsilat ve teminat birimi devreye alinsin.",
            "Aksiyon: yeni limit tahsisi durdurulsun, mevcut riskin teminatlandirilmasi icin 15 gun sure.",
        ]
    elif kantitatif_tetik or nitel_tetik:
        satirlar += [
            "Oneri: 2. ASAMA — yakin izleme. Omur boyu beklenen zarar karsiligina gecis onerilir.",
            "Aksiyon: aylik nakit akim tablosu istensin, limitler dondurulsun, teminat guncellemesi yapilsin.",
        ]
    else:
        satirlar.append("Oneri: 1. ASAMA devam. Standart izleme, ceyreklik gozden gecirme.")

    if ispatsiz_iyilesme_beyani:
        satirlar.append("Not: iyilesme beyani belgesiz. Yeni alici sozlesmesi ibraz edilmeden limit artisi degerlendirilmesin.")
    if yanit.ana_risk.confidence < 0.6:
        satirlar.append("Not: ana risk surucusu belirsiz — dosya kredi izleme uzmanina yazili gorus icin gonderilsin.")

    print()
    print("=" * 72)
    for satir in satirlar:
        print(satir)
    print("=" * 72)

    u = yanit.usage
    print(f"\nKullanim: {u.input_tokens} giris / {u.output_tokens} cikis token")


if __name__ == "__main__":
    try:
        main()
    except TypeSafeAuthenticationError:
        print("API anahtarı reddedildi. API_KEY satırındaki değer doğru mu?")
    except TypeSafeAPIConnectionError as hata:
        print(f"api.typesafe.ai'a bağlanılamadı (proxy/TLS?): {hata}")
    except TypeSafeError as hata:
        print(f"TypeSafe hatası: {hata}")
