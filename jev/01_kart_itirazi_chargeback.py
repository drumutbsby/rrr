"""01 — Kredi kartı harcama itirazı: chargeback uygunluğu.

Senaryo:  Müşteri e-ticaret alışverişinde ürünün teslim edilmediğini söyleyip
          itiraz açıyor. Kart operasyon ekibi, işlemin ters ibraz (chargeback)
          kuralına girip girmediğine ve hangi gerekçe koduyla açılacağına karar verir.

Jev'e sorulan:  müşterinin anlattığı olayın hangi itiraz kalıbına uyduğu, satıcıyla
                temas edilip edilmediği, dijital/fiziksel teslimat ayrımı.
Kodda kalan:    120 günlük süre kontrolü, tutar eşiği, gerekçe kodu eşlemesi.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 01_kart_itirazi_chargeback.py
"""

import os
from datetime import date

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


ISLEM_TARIHI = date(2026, 6, 14)
BASVURU_TARIHI = date(2026, 9, 20)
TUTAR = 12_400.0

STATE = {
    "kanal": "mobil_uygulama_itiraz_formu",
    "kart": {"tip": "kredi_karti", "3d_secure": False, "yurtdisi": True},
    "islem": {
        "isyeri": "GLOBALTECH STORE / NL",
        "mcc": 5732,
        "tutar_tl": TUTAR,
        "tarih": ISLEM_TARIHI.isoformat(),
    },
    "musteri_aciklamasi": (
        "14 Haziran'da yurtdışı bir siteden telefon siparişi verdim, kartımdan 12.400 TL çekildi. "
        "Kargo takip numarası verdiler ama kargo hiç hareket etmedi, ürün elime ulaşmadı. "
        "Satıcıya üç kez mail attım, iki tanesine hiç cevap vermediler, sonuncusunda "
        "'kargoya verildi' yazıp kestiler. İade de yapmıyorlar. Bankadan paramı geri istiyorum."
    ),
}

SORULAR = {
    "mal_teslim_edilmedi": Noul(
        instructions="The cardholder states that goods or services paid for were never received.",
        criteria={
            "true": "The cardholder says the purchased item or service was not delivered or not provided.",
            "false": "The item was received, or the dispute is about quality, price, duplicate billing, or an unrecognised charge.",
        },
    ),
    "islemi_kendi_yapmadi": Noul(
        instructions="The cardholder denies authorising the transaction at all.",
        criteria={
            "true": "The cardholder says they did not make or authorise this purchase.",
            "false": "The cardholder admits making the purchase but is unhappy with the outcome.",
        },
    ),
    "satici_ile_cozum_denendi": Noul(
        instructions=(
            "The cardholder describes having already contacted the merchant to resolve the problem "
            "before coming to the bank."
        ),
        criteria={
            "true": "The cardholder contacted the merchant (email, phone, ticket) and got no resolution.",
            "false": "There is no sign the cardholder tried the merchant first.",
        },
    ),
    "dijital_teslimat": Noul(
        instructions="The purchase is a digital good or service delivered online rather than a physical shipment.",
    ),
    "itiraz_kalibi": Choice(
        instructions="Which dispute pattern does the cardholder's account fit best?",
        criteria={
            "mal_hizmet_alinmadi": "Paid for goods or services that were never delivered or provided.",
            "yetkisiz_islem": "The cardholder says the transaction was not made by them at all.",
            "cift_cekim": "The same purchase was charged more than once.",
            "iptal_iade_yapilmadi": "The order was cancelled or returned but the refund never arrived.",
            "urun_farkli": "The item arrived but is materially different from what was described.",
            "abonelik_devam": "A subscription kept charging after the cardholder cancelled it.",
        },
    ),
    "kanit_yeterliligi": Score(
        instructions="How well does the cardholder's own account support opening a dispute without asking for more documents?",
        criteria=[
            "Vague: no dates, no merchant contact, no order details.",
            "Partial: the story is clear but key evidence (order number, correspondence, tracking) is missing.",
            "Strong: dates, merchant contact attempts and the merchant's response are all described.",
        ],
    ),
}

# Kart şemalarının ters ibraz süresi: işlem/beklenen teslim tarihinden itibaren 120 gün.
GEREKCE_KODU = {
    "mal_hizmet_alinmadi": "13.1 Merchandise/Services Not Received",
    "yetkisiz_islem": "10.4 Other Fraud - Card Absent Environment",
    "cift_cekim": "12.6.1 Duplicate Processing",
    "iptal_iade_yapilmadi": "13.6 Credit Not Processed",
    "urun_farkli": "13.3 Not as Described or Defective Merchandise",
    "abonelik_devam": "13.2 Cancelled Recurring Transaction",
}


def main() -> None:
    print("### Kart itirazi / chargeback uygunlugu\n")

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
    gun = (BASVURU_TARIHI - ISLEM_TARIHI).days
    sure_doldu = gun > 120
    kalip = c["itiraz_kalibi"].choice
    kod = GEREKCE_KODU.get(kalip, "-")

    satirlar = [f"Itiraz suresi: {gun} gun (limit 120) | Tutar: {TUTAR:,.0f} TL | Gerekce: {kod}"]

    if sure_doldu:
        satirlar.append("Karar: ters ibraz suresi dolmus. Musteriye yazili ret, satici ile dogrudan cozum onerilir.")
    elif n["islemi_kendi_yapmadi"].noul > 0.7:
        # Yetkisiz işlem iddiası chargeback değil, önce fraud hattı: kart bloke + tutanak.
        satirlar.append("Karar: yetkisiz islem iddiasi. Karti bloke et, fraud tutanagi ac, 10.4 kodundan ilerle.")
    elif c["itiraz_kalibi"].confidence < 0.6:
        satirlar.append("Karar: itiraz kalibi belirsiz. Dosyayi kart operasyon uzmanina kuyrukla.")
    elif n["mal_teslim_edilmedi"].noul > 0.7 and not n["satici_ile_cozum_denendi"].noul > 0.5:
        # Şema kuralı: 13.1'de önce satıcıyla temas şartı aranır.
        satirlar.append("Karar: once satici ile temas sarti. Musteriden yazismalari iste, dosyayi beklet.")
    elif s["kanit_yeterliligi"].score >= 1.5:
        satirlar.append(f"Karar: {kod} kodundan ters ibraz ac. Gecici alacak kaydi gir, saticiya 45 gun sure ver.")
    else:
        satirlar.append(f"Karar: {kod} kodu uygun ancak kanit zayif. Siparis no + yazisma talep et, sonra ac.")

    if n["dijital_teslimat"].noul > 0.6:
        satirlar.append("Not: dijital teslimat iddiasi var; IP/indirme logu saticidan ek kanit olarak istenmeli.")

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
