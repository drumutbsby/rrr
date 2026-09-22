"""04 — KOBİ kredi başvurusu ön değerlendirme (dosya triyajı).

Senaryo:  Şube, 3.000.000 TL işletme kredisi başvurusu açıyor. Kredi tahsis birimine
          gitmeden önce dosyanın eksiksiz mi, beyanların tutarlı mı olduğu ve
          hangi kuyruğa düşeceği belirleniyor.

Jev'e sorulan:  serbest metin (şube görüşme notu + faaliyet açıklaması) ile sayısal
                tablonun birbirini tutup tutmadığı, kredi amacının ne olduğu.
Kodda kalan:    rasyolar (borç/özkaynak, DSCR), limit eşikleri, yetki kademesi.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 04_kobi_kredi_on_degerlendirme.py
"""

import os

from typesafe_sdk import (
    Choice,
    Noul,
    Score,
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


TALEP_TUTARI = 3_000_000.0

FINANSAL = {
    "net_satis_tl": 41_200_000,
    "faaliyet_kari_tl": 3_050_000,
    "faiz_amortisman_oncesi_kar_tl": 4_100_000,
    "toplam_finansal_borc_tl": 9_800_000,
    "ozkaynak_tl": 5_200_000,
    "yillik_borc_servisi_tl": 3_400_000,
    "stok_devir_gun": 118,
    "alacak_tahsil_gun": 96,
}

STATE = {
    "firma": {
        "unvan": "ÖRNEK MAKİNA SAN. TİC. LTD. ŞTİ.",
        "sektor": "metal_isleme",
        "faaliyet_yili": 14,
        "calisan": 38,
        "kredi_notu": 1_240,
    },
    "talep": {"urun": "isletme_kredisi", "tutar_tl": TALEP_TUTARI, "vade_ay": 36, "teminat": "ipotek_2_derece"},
    "finansal": FINANSAL,
    "sube_notu": (
        "Firma sahibiyle görüşüldü. Son iki yıl ciro büyümesi güçlü ancak büyümenin tamamı "
        "tek bir otomotiv yan sanayi müşterisinden geliyor; bu müşteriden alacak vadesi "
        "90 günü aşmış durumda. Ortak, 'yeni CNC tezgâhı alacağız, ödemesini peşin yapacağız' "
        "dedi, ancak talep işletme kredisi olarak açıldı. Geçen yıl iki çek karşılıksız çıkmış, "
        "aynı gün kapatılmış. Bilanço 2025 yıl sonu; 2026 ara dönem verisi henüz verilmedi. "
        "Ortakların başka bir firmada da ortaklığı olduğu söylendi, detay paylaşılmadı."
    ),
}

SORULAR = {
    "amac_tutarsiz": Noul(
        instructions="The stated use of the loan contradicts the product the application was opened under.",
        criteria={
            "true": "The borrower describes an investment or asset purchase while the application is for working capital, or vice versa.",
            "false": "The described use matches the requested product.",
        },
    ),
    "musteri_yogunlasmasi": Noul(
        instructions="The company's revenue depends heavily on a single customer or a very small number of customers.",
    ),
    "belge_eksik": Noul(
        instructions="Required financial or ownership documents are described as missing, outdated or not provided.",
    ),
    "gizlenen_iliski": Noul(
        instructions=(
            "There are related parties or affiliated companies whose details the borrower avoided sharing."
        ),
    ),
    "odeme_disiplini_sorunu": Noul(
        instructions="The record mentions past payment failures such as bounced cheques, arrears or restructured debt.",
    ),
    "kredi_amaci": Choice(
        instructions="What is the loan really going to be used for, based on the branch note?",
        criteria={
            "isletme_sermayesi": "Day-to-day working capital: stock, payroll, supplier payments.",
            "yatirim": "Buying machinery, property or other fixed assets.",
            "borc_kapatma": "Repaying or refinancing existing debt.",
            "alacak_finansmani": "Bridging receivables that customers have not yet paid.",
            "belirsiz": "The purpose cannot be determined from the file.",
        },
    ),
    "dosya_kalitesi": Score(
        instructions="How ready is this credit file for a decision without further information?",
        criteria=[
            "Not ready: key documents or explanations are missing.",
            "Partly ready: decision possible but conditions or extra documents are needed.",
            "Ready: file is complete and internally consistent.",
        ],
    ),
}


def main() -> None:
    print("### KOBI kredi basvurusu on degerlendirme\n")

    if PROXY:
        os.environ["HTTPS_PROXY"] = PROXY

    with TypeSafeClient(api_key=anahtar(), timeout=30) as client:
        yanit = client.system_one(state=STATE, questions=SORULAR)
    print(f"Model: {yanit.model}\n")

    for ad, cevap in yanit.nouls.items():
        print(f"[Noul]   {ad:<26} p(evet) = {cevap.noul:.3f}")

    for ad, cevap in yanit.choices.items():
        dagilim = ", ".join(f"{k}={v:.2f}" for k, v in sorted(cevap.probabilities.items(), key=lambda kv: -kv[1]))
        print(f"[Choice] {ad:<26} secim = {cevap.choice}  (guven {cevap.confidence:.2f})  [{dagilim}]")

    for ad, cevap in yanit.scores.items():
        seviyeler = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(cevap.probabilities.items()))
        print(f"[Score]  {ad:<26} beklenen = {cevap.score:.2f}  (guven {cevap.confidence:.2f})  [{seviyeler}]")

    n, c, s = yanit.nouls, yanit.choices, yanit.scores

    # Rasyolar koda ait: model sayı hesaplamıyor, metin ile tabloyu karşılaştırıyor.
    borc_ozkaynak = FINANSAL["toplam_finansal_borc_tl"] / FINANSAL["ozkaynak_tl"]
    dscr = FINANSAL["faiz_amortisman_oncesi_kar_tl"] / FINANSAL["yillik_borc_servisi_tl"]
    nakit_dongusu = FINANSAL["stok_devir_gun"] + FINANSAL["alacak_tahsil_gun"]

    satirlar = [
        f"Borc/Ozkaynak: {borc_ozkaynak:.2f} (limit 2.00) | DSCR: {dscr:.2f} (limit 1.25) | "
        f"Nakit dongusu: {nakit_dongusu} gun",
        f"Talep: {TALEP_TUTARI:,.0f} TL | Algilanan amac: {c['kredi_amaci'].choice} "
        f"(guven {c['kredi_amaci'].confidence:.2f})",
    ]

    kirmizi = []
    if borc_ozkaynak > 2.0:
        kirmizi.append("borc/ozkaynak limit ustu")
    if dscr < 1.25:
        kirmizi.append("borc servisi karsilama yetersiz")
    if n["musteri_yogunlasmasi"].noul > 0.7:
        kirmizi.append("tek musteri yogunlasmasi")
    if n["gizlenen_iliski"].noul > 0.6:
        kirmizi.append("beyan edilmeyen iliskili taraf")
    if n["odeme_disiplini_sorunu"].noul > 0.6:
        kirmizi.append("gecmis odeme disiplini")

    if n["belge_eksik"].noul > 0.6 or s["dosya_kalitesi"].score < 0.8:
        satirlar.append("Karar: DOSYA EKSIK. Ara donem bilanco + ortaklik yapisi istensin, tahsise gonderilmesin.")
    elif n["amac_tutarsiz"].noul > 0.7:
        satirlar.append(
            f"Karar: URUN DEGISIKLIGI. Talep {c['kredi_amaci'].choice} gorunuyor; "
            "yatirim kredisi olarak yeniden yapilandirilsin."
        )
    elif len(kirmizi) >= 3:
        satirlar.append("Karar: UST YETKI. Genel mudurluk kredi komitesine, teminat guclendirme sarti ile.")
    elif kirmizi:
        satirlar.append("Karar: SARTLI ON ONAY. Bolge kredi tahsise; ipotek 1. dereceye alinmasi sarti eklensin.")
    else:
        satirlar.append("Karar: STANDART AKIS. Sube yetkisinde tahsis surecine girsin.")

    satirlar.append(f"Kirmizi bayraklar: {', '.join(kirmizi) if kirmizi else '-'}")
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
