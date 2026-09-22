"""08 — Bireysel kredi yapılandırma talebi (serbest metin e-posta).

Senaryo:  Müşteri, henüz gecikmeye düşmeden yapılandırma istiyor. Gelen kutusuna
          günde yüzlerce böyle e-posta düşüyor; hangi ürünün teklif edileceği ve
          hangilerinin belge istemeden karara bağlanabileceği ayrıştırılmalı.

Jev'e sorulan:  e-postanın gerçekten yapılandırma talebi mi olduğu, zorluğun
                geçici/kalıcı olduğu, hangi çözümün istendiği, şikâyet tonu.
Kodda kalan:    ürün uygunluk matrisi, kalan vade, taksit/gelir oranı.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 08_yapilandirma_talebi.py
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


DOSYA = {
    "urun": "konut_kredisi",
    "kalan_anapara_tl": 1_240_000,
    "kalan_vade_ay": 84,
    "aylik_taksit_tl": 21_800,
    "beyan_gelir_tl": 46_000,
    "gecikme_gun": 0,
    "onceki_yapilandirma": False,
}

STATE = {
    "dosya": DOSYA,
    "kanal": "e_posta",
    "konu": "Kredi taksitim hakkında",
    "metin": (
        "Merhaba,\n\n"
        "2021'de kullandığım konut kredisinin taksitini bugüne kadar hiç aksatmadım. "
        "Ancak çalıştığım şirket eylül ayında kısa çalışma ödeneğine geçti, maaşımın %40'ını "
        "alıyorum ve bu durumun en az 4-5 ay süreceği söylendi. Eşim çalışmıyor, iki çocuğum var.\n\n"
        "Taksitimi ödeyemeyeceğim aşamaya gelmeden size yazmak istedim. Önümüzdeki 6 ay için "
        "taksitimi düşürebilir miyiz, vadeyi uzatmak da olur. Ya da 3 ay sadece faiz ödeyeyim, "
        "sonra normale döneyim. Sicilimin bozulmasını istemiyorum.\n\n"
        "Şubeye iki kez gittim, 'gecikmeye düşmeden bir şey yapamayız' dediler. "
        "Bu bana çok mantıksız geldi, gecikmeye düşmemi mi bekliyorsunuz? "
        "Gerekirse BDDK'ya da yazacağım ama önce sizden çözüm bekliyorum.\n\n"
        "İyi çalışmalar."
    ),
}

SORULAR = {
    "yapilandirma_talebi": Noul(
        instructions="The message asks the bank to change the terms of an existing loan.",
    ),
    "gecici_zorluk": Noul(
        instructions="The difficulty described is temporary with a foreseeable end, rather than permanent.",
        criteria={
            "true": "The customer names a limited period or an expected recovery (reduced hours, short-term leave, seasonal drop).",
            "false": "The income loss looks permanent or open-ended.",
        },
    ),
    "proaktif_basvuru": Noul(
        instructions="The customer is reaching out before missing a payment rather than after falling behind.",
    ),
    "sikayet_tonu": Noul(
        instructions="The message contains a complaint about how the bank or a branch handled the customer.",
    ),
    "regulator_tehdidi": Noul(
        instructions="The customer threatens to escalate to a regulator, ombudsman, consumer arbitration or the press.",
    ),
    "istenen_cozum": Choice(
        instructions="What relief is the customer actually asking for?",
        criteria={
            "vade_uzatimi": "Extend the term so the monthly instalment falls.",
            "odemesiz_donem": "A payment holiday for a number of months.",
            "sadece_faiz": "Pay interest only for a period, then return to normal.",
            "faiz_indirimi": "A lower interest rate.",
            "tam_kapatma_indirimi": "A discount to settle the debt in one payment.",
            "bilgi_talebi": "No relief requested; the customer only wants information.",
        },
    ),
    "odeme_kapasitesi": Score(
        instructions="How much of the current instalment can this customer sustain during the difficulty?",
        criteria=[
            "Almost none: needs a full payment holiday.",
            "Partial: can pay a reduced instalment.",
            "Most of it: a small adjustment is enough.",
        ],
    ),
}

# Ürün uygunluk matrisi koda ait: modelin işi talebi anlamak, ürünü seçmek değil.
URUN_KURALI = {
    "vade_uzatimi": lambda d: d["kalan_vade_ay"] <= 96,
    "odemesiz_donem": lambda d: d["gecikme_gun"] == 0 and not d["onceki_yapilandirma"],
    "sadece_faiz": lambda d: d["kalan_anapara_tl"] >= 250_000,
    "faiz_indirimi": lambda d: False,          # bireysel konutta fiyat degisikligi yetkisi tahsiste
    "tam_kapatma_indirimi": lambda d: False,   # sadece takipteki dosyalarda
    "bilgi_talebi": lambda d: True,
}


def main() -> None:
    print("### Bireysel kredi yapilandirma talebi\n")

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
    talep = c["istenen_cozum"].choice
    uygun = URUN_KURALI.get(talep, lambda d: False)(DOSYA)
    taksit_gelir = DOSYA["aylik_taksit_tl"] / DOSYA["beyan_gelir_tl"]
    dusuk_gelirle_taksit_gelir = DOSYA["aylik_taksit_tl"] / (DOSYA["beyan_gelir_tl"] * 0.40)

    satirlar = [
        f"Talep: {talep} (guven {c['istenen_cozum'].confidence:.2f}) | Urun uygun mu: {'evet' if uygun else 'hayir'}",
        f"Taksit/gelir: normalde {taksit_gelir:.0%}, kisa calismada {dusuk_gelirle_taksit_gelir:.0%}",
    ]

    if n["yapilandirma_talebi"].noul < 0.5:
        satirlar.append("Karar: yapilandirma talebi degil. Bilgilendirme yaniti, standart SLA.")
    elif c["istenen_cozum"].confidence < 0.55:
        satirlar.append("Karar: talep belirsiz. Musteri aransin, tercih netlestirilsin.")
    elif n["gecici_zorluk"].noul > 0.6 and s["odeme_kapasitesi"].score >= 1.0 and uygun:
        satirlar.append(f"Karar: {talep} teklif edilsin. 6 ay indirimli taksit + sonrasinda orijinal plana donus.")
    elif n["gecici_zorluk"].noul > 0.6 and s["odeme_kapasitesi"].score < 1.0:
        satirlar.append("Karar: 3 ay odemesiz donem + vade uzatimi kombinasyonu; kisa calisma belgesi istensin.")
    elif not uygun:
        satirlar.append(f"Karar: talep edilen urun ({talep}) bu dosyaya uygun degil. Alternatif olarak vade uzatimi teklif edilsin.")
    else:
        satirlar.append("Karar: kalici gelir kaybi ihtimali. Gelir belgesi + detayli butce calismasi ile tahsise gonderilsin.")

    # Proaktif başvuruyu ödüllendirmek riski düşürür: gecikmeye düşmeden çözüm sicili korur.
    if n["proaktif_basvuru"].noul > 0.7:
        satirlar.append("Not: gecikmesiz proaktif basvuru. 'Once gecikmeye dus' yanlis yonlendirmesi duzeltilsin, sicil korunur.")
    if n["sikayet_tonu"].noul > 0.6:
        satirlar.append("Aksiyon: sube yonlendirmesi hakkinda sikayet kaydi acilsin, bolge mudurlugune geri bildirim.")
    if n["regulator_tehdidi"].noul > 0.6:
        satirlar.append("Aksiyon: BDDK/THH eskalasyon riski — yanit 3 is gunu icinde ve yazili gerekceli verilsin.")

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
