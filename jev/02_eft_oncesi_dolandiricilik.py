"""02 — Gönderim öncesi EFT/FAST müdahalesi (ikna edilmiş müşteri dolandırıcılığı).

Senaryo:  Müşteri mobil uygulamadan ilk kez gördüğü bir IBAN'a yüksek tutarlı FAST
          gönderimi yapmak istiyor. Kural motoru işlemi "teyit" kuyruğuna düşürüyor,
          çağrı merkezi müşteriyi arıyor. Konuşmanın özeti + hesap sinyalleri Jev'e gidiyor.

Jev'e sorulan:  müşterinin anlattığı hikâyenin bilinen dolandırıcılık senaryolarına
                (sahte yatırım, sahte polis/savcı, romantizm, sahte emlak) uyup uymadığı,
                müşterinin yönlendirilmiş/telkin altında olup olmadığı.
Kodda kalan:    tutar eşiği, gecikmeli gönderim kuralı, bloke ve MASAK bildirim tetikleri.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 02_eft_oncesi_dolandiricilik.py
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


TUTAR = 185_000.0

STATE = {
    "islem": {
        "tip": "FAST",
        "tutar_tl": TUTAR,
        "alici_iban_yeni": True,
        "alici_ad": "M** K**",
        "aciklama": "borc odemesi",
        "saat": "22:41",
    },
    "hesap_gecmisi": {
        "ortalama_aylik_giden_tl": 9_500,
        "son_24_saat": ["vadeli hesap bozuldu: 150.000 TL", "kredi kullanimi: 50.000 TL"],
        "musteri_yasi": 63,
        "kanal": "mobil",
    },
    "cagri_ozeti": (
        "Müşteri, üç haftadır bir yatırım danışmanıyla WhatsApp'tan görüştüğünü söyledi. "
        "Ekran paylaşımıyla bir platformda kâr ettiğini gösteriyorlarmış, ilk 20 bin lirayı "
        "çekebilmiş. Şimdi 'kâr payını çekmek için teminat yatırman gerek' demişler. "
        "Görüşme sırasında müşteri temsilcisine 'bankaya borç ödemesi yaz dediler, "
        "yoksa işlem gecikirmiş' dedi. Arama boyunca yanında biri olduğu ve ona ne "
        "söyleyeceğini fısıldadığı duyuldu. Aceleci, teyit sorularına kısa cevap veriyor."
    ),
}

SORULAR = {
    "yonlendirilmis_odeme": Noul(
        instructions=(
            "The customer is being coached or instructed by a third party about how to answer the "
            "bank and how to label the transfer."
        ),
        criteria={
            "true": "Someone is telling the customer what to say to the bank, or the stated purpose was supplied by that third party.",
            "false": "The customer explains the payment in their own words with no outside coaching.",
        },
    ),
    "yatirim_vaadi": Noul(
        instructions="The customer describes an investment opportunity with promised or already shown profits.",
    ),
    "aciklama_tutarsiz": Noul(
        instructions="The stated purpose of the transfer contradicts what the customer actually describes.",
        criteria={
            "true": "The reference or reason given for the payment does not match the customer's own account of it.",
            "false": "The stated purpose matches the customer's explanation.",
        },
    ),
    "baski_altinda": Noul(
        instructions="The customer appears to be under pressure, urgency or fear while making this payment.",
    ),
    "senaryo": Choice(
        instructions="Which known payment-fraud pattern best matches the customer's story?",
        criteria={
            "sahte_yatirim": "A fake investment or trading platform showing profits and asking for more deposits.",
            "kamu_gorevlisi_taklidi": "Someone posing as police, prosecutor, tax office or the bank's own security team.",
            "romantizm": "A romantic or online relationship asking for money.",
            "sahte_satici": "Payment for goods, property or a rental from a seller the customer never met.",
            "yakin_taklidi": "Someone posing as a family member or friend in urgent need.",
            "mesru_odeme": "A genuine payment with no fraud pattern: known counterparty, ordinary purpose.",
        },
    ),
    "zarar_riski": Score(
        instructions="How likely is it that this money is lost for good once it leaves the account?",
        criteria=[
            "Low: ordinary payment to a plausible counterparty, funds recoverable if wrong.",
            "Medium: some fraud indicators, but the story could be genuine.",
            "High: multiple classic fraud indicators; funds will very likely be moved on immediately.",
        ],
    ),
}


def main() -> None:
    print("### EFT/FAST oncesi dolandiricilik mudahalesi\n")

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

    # Sinyaller ayrı ayrı zayıf olabilir; birleştirme burada, modelde değil.
    ikna_gostergesi = sum(
        [
            n["yonlendirilmis_odeme"].noul > 0.6,
            n["aciklama_tutarsiz"].noul > 0.6,
            n["baski_altinda"].noul > 0.6,
            n["yatirim_vaadi"].noul > 0.6,
        ]
    )
    yuksek_tutar = TUTAR >= 50_000
    senaryo = c["senaryo"].choice
    kritik = s["zarar_riski"].score >= 1.5

    satirlar = [
        f"Tutar: {TUTAR:,.0f} TL | Ikna gostergesi: {ikna_gostergesi}/4 | Senaryo: {senaryo} "
        f"(guven {c['senaryo'].confidence:.2f})"
    ]

    if ikna_gostergesi >= 3 and kritik and yuksek_tutar:
        satirlar += [
            "Karar: ISLEMI DURDUR. Gonderim iptal, hesaba 24 saat cikis kisiti.",
            "Aksiyon: sube/fraud ekibi musteriyi geri arasin, yuz yuze teyit istensin.",
            "Aksiyon: alici IBAN muhabir bankaya bildirilsin, MASAK supheli islem degerlendirmesi acilsin.",
        ]
    elif ikna_gostergesi >= 2 and kritik:
        satirlar += [
            "Karar: GECIKMELI GONDERIM. Islem 24 saat bekletilsin, musteri ertesi gun tekrar teyit edilsin.",
            "Aksiyon: musteriye senaryoya ozel uyari metni gosterilsin (teminat isteyen platform = dolandiricilik).",
        ]
    elif c["senaryo"].confidence < 0.55 or s["zarar_riski"].confidence < 0.55:
        satirlar.append("Karar: sinyal belirsiz. Dosya fraud analistine, islem teyide kadar beklemede.")
    elif senaryo == "mesru_odeme" and ikna_gostergesi == 0:
        satirlar.append("Karar: islem serbest. Standart izleme.")
    else:
        satirlar.append("Karar: islem serbest ancak isaretli. Alici IBAN izleme listesine, 7 gun tekrar kontrol.")

    if n["baski_altinda"].noul > 0.7 and STATE["hesap_gecmisi"]["musteri_yasi"] >= 60:
        satirlar.append("Not: korunmasiz musteri protokolu — gorusme kaydi saklansin, ikinci kontrol zorunlu.")

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
