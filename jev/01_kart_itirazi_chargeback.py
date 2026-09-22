"""01 — Kredi kartı harcama itirazı: chargeback uygunluğu.

Senaryo:  Müşteri e-ticaret alışverişinde ürünün teslim edilmediğini söyleyip
          itiraz açıyor. Kart operasyon ekibi, işlemin ters ibraz (chargeback)
          kuralına girip girmediğine ve hangi gerekçe koduyla açılacağına karar verir.

Jev'e sorulan:  müşterinin anlattığı olayın hangi itiraz kalıbına uyduğu, satıcıyla
                temas edilip edilmediği, dijital/fiziksel teslimat ayrımı.
Kodda kalan:    120 günlük süre kontrolü, tutar eşiği, gerekçe kodu eşlemesi.

Çalıştırma: python jev/01_kart_itirazi_chargeback.py
"""

from datetime import date

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

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
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

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

    karar(satirlar)


if __name__ == "__main__":
    calistir("Kart itirazi / chargeback uygunlugu", main)
