"""Jev (TypeSafe AI) — PyQt deneme uygulaması.

Ne yapar:
  * 10 hazır bankacılık senaryosu gömülü gelir (soldaki listeden seç, çalıştır).
  * State ve Questions panolarını düzenleyebilirsin; gönderilen şey ekranda gördüğündür.
  * Dışarıdan JSON talimat yükleyebilirsin (Dosya > JSON yükle, ya da pencereye sürükle-bırak).
    Biçim otomatik algılanır:
      - {"state": {...}, "questions": {...}}                         -> tek senaryo
      - {"ad": {"baslik": ..., "state": ..., "questions": ...}, ...}  -> çoklu senaryo
      - {"soru_adi": {"type": "noul", ...}, ...}                      -> yalnızca sorular
      - başka her JSON nesnesi/dizisi                                 -> yalnızca state
  * Cevapları olasılık çubuklarıyla gösterir; gömülü senaryolarda eşik/karar bloğunu da çalıştırır.

Kurulum:  pip install typesafe-sdk PyQt6      (PyQt5 de çalışır)
Anahtar:  Aşağıdaki API_KEY satırına yapıştır; boşsa TYPESAFE_API_KEY ortam
          değişkeni okunur. Arayüzdeki alandan da girebilirsin.
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma:  python jev/jev_pyqt.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from typesafe_sdk import (
    Choice,
    Noul,
    Score,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeRateLimitError,
)

try:  # PyQt6 tercih edilir, kurumsal makinelerde PyQt5 de olabilir
    from PyQt6 import QtCore, QtGui, QtWidgets

    QT_SURUM = 6
except ImportError:  # pragma: no cover - ortama bagli
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore[no-redef]

    QT_SURUM = 5


API_KEY = ""   # <-- anahtarı buraya yapıştır: API_KEY = "ts-..."
PROXY = ""     # <-- kurumsal proxy varsa buraya, yoksa boş bırak
MODEL = ""     # <-- belirli bir model denemek istersen, boşsa hesabın varsayılanı


# --- PyQt5/PyQt6 enum farkını kapatan küçük yardımcı ------------------------------------------
def _enum(kok: Any, sinif: str, uye: str) -> Any:
    """PyQt6'da Qt.Orientation.Horizontal, PyQt5'te Qt.Horizontal."""
    return getattr(getattr(kok, sinif, kok), uye)


YATAY = _enum(QtCore.Qt, "Orientation", "Horizontal")
DIKEY = _enum(QtCore.Qt, "Orientation", "Vertical")
KULLANICI_ROL = _enum(QtCore.Qt, "ItemDataRole", "UserRole")
SIFRE_MODU = _enum(QtWidgets.QLineEdit, "EchoMode", "Password")
SARMA_YOK = _enum(QtWidgets.QPlainTextEdit, "LineWrapMode", "NoWrap")


@dataclass
class Senaryo:
    """Bir deneme senaryosu: state + sorular + (varsa) karar mantığı."""

    baslik: str
    aciklama: str
    state: Any
    sorular: dict[str, Any]          # JSON'a çevrilmiş soru sözlüğü
    karar: Callable[[SystemOneResponse], list[str]] | None = None


def _sorular(**tanimlar: Any) -> dict[str, Any]:
    """Noul/Choice/Score nesnelerini panoda gösterilecek JSON sözlüğüne çevirir."""
    return {ad: soru.model_dump(mode="json") for ad, soru in tanimlar.items()}


# ==============================================================================================
# 01 — Kart itirazı / chargeback uygunluğu
# ==============================================================================================
S01_ISLEM_TARIHI = date(2026, 6, 14)
S01_BASVURU_TARIHI = date(2026, 9, 20)
S01_TUTAR = 12_400.0

S01_STATE = {
    "kanal": "mobil_uygulama_itiraz_formu",
    "kart": {"tip": "kredi_karti", "3d_secure": False, "yurtdisi": True},
    "islem": {
        "isyeri": "GLOBALTECH STORE / NL",
        "mcc": 5732,
        "tutar_tl": S01_TUTAR,
        "tarih": S01_ISLEM_TARIHI.isoformat(),
    },
    "musteri_aciklamasi": (
        "14 Haziran'da yurtdışı bir siteden telefon siparişi verdim, kartımdan 12.400 TL çekildi. "
        "Kargo takip numarası verdiler ama kargo hiç hareket etmedi, ürün elime ulaşmadı. "
        "Satıcıya üç kez mail attım, iki tanesine hiç cevap vermediler, sonuncusunda "
        "'kargoya verildi' yazıp kestiler. İade de yapmıyorlar. Bankadan paramı geri istiyorum."
    ),
}

S01_SORULAR = _sorular(
    mal_teslim_edilmedi=Noul(
        instructions="The cardholder states that goods or services paid for were never received.",
        criteria={
            "true": "The cardholder says the purchased item or service was not delivered or not provided.",
            "false": "The item was received, or the dispute is about quality, price, duplicate billing, or an unrecognised charge.",
        },
    ),
    islemi_kendi_yapmadi=Noul(
        instructions="The cardholder denies authorising the transaction at all.",
        criteria={
            "true": "The cardholder says they did not make or authorise this purchase.",
            "false": "The cardholder admits making the purchase but is unhappy with the outcome.",
        },
    ),
    satici_ile_cozum_denendi=Noul(
        instructions=(
            "The cardholder describes having already contacted the merchant to resolve the problem "
            "before coming to the bank."
        ),
        criteria={
            "true": "The cardholder contacted the merchant (email, phone, ticket) and got no resolution.",
            "false": "There is no sign the cardholder tried the merchant first.",
        },
    ),
    dijital_teslimat=Noul(
        instructions="The purchase is a digital good or service delivered online rather than a physical shipment.",
    ),
    itiraz_kalibi=Choice(
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
    kanit_yeterliligi=Score(
        instructions="How well does the cardholder's own account support opening a dispute without asking for more documents?",
        criteria=[
            "Vague: no dates, no merchant contact, no order details.",
            "Partial: the story is clear but key evidence (order number, correspondence, tracking) is missing.",
            "Strong: dates, merchant contact attempts and the merchant's response are all described.",
        ],
    ),
)

S01_GEREKCE_KODU = {
    "mal_hizmet_alinmadi": "13.1 Merchandise/Services Not Received",
    "yetkisiz_islem": "10.4 Other Fraud - Card Absent Environment",
    "cift_cekim": "12.6.1 Duplicate Processing",
    "iptal_iade_yapilmadi": "13.6 Credit Not Processed",
    "urun_farkli": "13.3 Not as Described or Defective Merchandise",
    "abonelik_devam": "13.2 Cancelled Recurring Transaction",
}


def karar_01(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    gun = (S01_BASVURU_TARIHI - S01_ISLEM_TARIHI).days
    kalip = c["itiraz_kalibi"].choice
    kod = S01_GEREKCE_KODU.get(kalip, "-")
    satirlar = [f"İtiraz süresi: {gun} gün (limit 120) | Tutar: {S01_TUTAR:,.0f} TL | Gerekçe: {kod}"]

    if gun > 120:
        satirlar.append("Karar: ters ibraz süresi dolmuş. Müşteriye yazılı ret, satıcı ile doğrudan çözüm önerilir.")
    elif n["islemi_kendi_yapmadi"].noul > 0.7:
        satirlar.append("Karar: yetkisiz işlem iddiası. Kartı bloke et, fraud tutanağı aç, 10.4 kodundan ilerle.")
    elif c["itiraz_kalibi"].confidence < 0.6:
        satirlar.append("Karar: itiraz kalıbı belirsiz. Dosyayı kart operasyon uzmanına kuyrukla.")
    elif n["mal_teslim_edilmedi"].noul > 0.7 and n["satici_ile_cozum_denendi"].noul <= 0.5:
        satirlar.append("Karar: önce satıcı ile temas şartı. Müşteriden yazışmaları iste, dosyayı beklet.")
    elif s["kanit_yeterliligi"].score >= 1.5:
        satirlar.append(f"Karar: {kod} kodundan ters ibraz aç. Geçici alacak kaydı gir, satıcıya 45 gün süre ver.")
    else:
        satirlar.append(f"Karar: {kod} kodu uygun ancak kanıt zayıf. Sipariş no + yazışma talep et, sonra aç.")

    if n["dijital_teslimat"].noul > 0.6:
        satirlar.append("Not: dijital teslimat iddiası var; IP/indirme logu satıcıdan ek kanıt olarak istenmeli.")
    return satirlar


# ==============================================================================================
# 02 — EFT/FAST öncesi dolandırıcılık müdahalesi
# ==============================================================================================
S02_TUTAR = 185_000.0

S02_STATE = {
    "islem": {
        "tip": "FAST",
        "tutar_tl": S02_TUTAR,
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

S02_SORULAR = _sorular(
    yonlendirilmis_odeme=Noul(
        instructions=(
            "The customer is being coached or instructed by a third party about how to answer the "
            "bank and how to label the transfer."
        ),
        criteria={
            "true": "Someone is telling the customer what to say to the bank, or the stated purpose was supplied by that third party.",
            "false": "The customer explains the payment in their own words with no outside coaching.",
        },
    ),
    yatirim_vaadi=Noul(
        instructions="The customer describes an investment opportunity with promised or already shown profits.",
    ),
    aciklama_tutarsiz=Noul(
        instructions="The stated purpose of the transfer contradicts what the customer actually describes.",
        criteria={
            "true": "The reference or reason given for the payment does not match the customer's own account of it.",
            "false": "The stated purpose matches the customer's explanation.",
        },
    ),
    baski_altinda=Noul(
        instructions="The customer appears to be under pressure, urgency or fear while making this payment.",
    ),
    senaryo=Choice(
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
    zarar_riski=Score(
        instructions="How likely is it that this money is lost for good once it leaves the account?",
        criteria=[
            "Low: ordinary payment to a plausible counterparty, funds recoverable if wrong.",
            "Medium: some fraud indicators, but the story could be genuine.",
            "High: multiple classic fraud indicators; funds will very likely be moved on immediately.",
        ],
    ),
)


def karar_02(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    ikna = sum(
        [
            n["yonlendirilmis_odeme"].noul > 0.6,
            n["aciklama_tutarsiz"].noul > 0.6,
            n["baski_altinda"].noul > 0.6,
            n["yatirim_vaadi"].noul > 0.6,
        ]
    )
    kritik = s["zarar_riski"].score >= 1.5
    yuksek_tutar = S02_TUTAR >= 50_000
    satirlar = [
        f"Tutar: {S02_TUTAR:,.0f} TL | İkna göstergesi: {ikna}/4 | "
        f"Senaryo: {c['senaryo'].choice} (güven {c['senaryo'].confidence:.2f})"
    ]

    if ikna >= 3 and kritik and yuksek_tutar:
        satirlar += [
            "Karar: İŞLEMİ DURDUR. Gönderim iptal, hesaba 24 saat çıkış kısıtı.",
            "Aksiyon: şube/fraud ekibi müşteriyi geri arasın, yüz yüze teyit istensin.",
            "Aksiyon: alıcı IBAN muhabir bankaya bildirilsin, MASAK şüpheli işlem değerlendirmesi açılsın.",
        ]
    elif ikna >= 2 and kritik:
        satirlar += [
            "Karar: GECİKMELİ GÖNDERİM. İşlem 24 saat bekletilsin, müşteri ertesi gün tekrar teyit edilsin.",
            "Aksiyon: müşteriye senaryoya özel uyarı metni gösterilsin (teminat isteyen platform = dolandırıcılık).",
        ]
    elif c["senaryo"].confidence < 0.55 or s["zarar_riski"].confidence < 0.55:
        satirlar.append("Karar: sinyal belirsiz. Dosya fraud analistine, işlem teyide kadar beklemede.")
    elif c["senaryo"].choice == "mesru_odeme" and ikna == 0:
        satirlar.append("Karar: işlem serbest. Standart izleme.")
    else:
        satirlar.append("Karar: işlem serbest ancak işaretli. Alıcı IBAN izleme listesine, 7 gün tekrar kontrol.")

    if n["baski_altinda"].noul > 0.7 and S02_STATE["hesap_gecmisi"]["musteri_yasi"] >= 60:
        satirlar.append("Not: korunmasız müşteri protokolü — görüşme kaydı saklansın, ikinci kontrol zorunlu.")
    return satirlar


# ==============================================================================================
# 03 — MASAK şüpheli işlem taraması (tek kayıt; diğer kayıtlar playground JSON'larında)
# ==============================================================================================
S03_STATE = {
    "musteri_no": "4471902",
    "profil": {"meslek": "ogrenci", "yas": 21, "beyan_gelir_tl": 0, "hesap_yasi_gun": 38},
    "hareketler": [
        "11 farkli gercek kisiden 3 gun icinde toplam 412.000 TL gelen havale",
        "Her gelen tutar 9.000-9.800 TL araliginda",
        "Gelen tutarlarin %94'u ayni gun icinde 3 farkli IBAN'a cikti",
        "Kalan bakiye: 2.140 TL",
    ],
}

S03_SORULAR = _sorular(
    parcalama=Noul(
        instructions=(
            "The account activity looks like structuring: amounts deliberately kept below a reporting "
            "threshold, or one large sum split across many smaller movements."
        ),
    ),
    gecis_hesabi=Noul(
        instructions=(
            "The account behaves as a pass-through: money arrives and leaves almost immediately, "
            "leaving little balance behind."
        ),
        criteria={
            "true": "Incoming funds are forwarded out within a very short time, with almost nothing retained.",
            "false": "Funds stay in the account and are used in a way consistent with normal personal or business use.",
        },
    ),
    profil_uyumsuz=Noul(
        instructions=(
            "The volume or nature of the activity is inconsistent with the customer's stated occupation, "
            "age and declared income."
        ),
    ),
    ekonomik_gerekce_var=Noul(
        instructions="The activity has a visible, documented business or economic rationale.",
        criteria={
            "true": "Invoices, contracts, payroll, progress payments or similar explain the flow.",
            "false": "No economic explanation is visible in the records.",
        },
    ),
    tipoloji=Choice(
        instructions="Which money-laundering typology does this activity fit best?",
        criteria={
            "para_katiri": "A mule account collecting funds from many senders and forwarding them on.",
            "nakit_yogun_yerlestirme": "Repeated cash deposits placing physical cash into the system.",
            "kripto_cikis": "Funds converted and moved to crypto exchanges or wallets.",
            "ticari_gorunumlu": "Flows disguised as trade or contracting payments.",
            "hesap_ele_gecirme": "The pattern suggests the account is controlled by someone other than the customer.",
            "olagan": "Ordinary activity consistent with the customer profile.",
        },
    ),
    sib_gerekcesi=Score(
        instructions="How strong is the case for filing a suspicious transaction report?",
        criteria=[
            "Weak: activity is explainable; monitor only.",
            "Moderate: unusual pattern that needs an analyst to request documents first.",
            "Strong: pattern matches a known typology with no plausible economic explanation.",
        ],
    ),
)


def karar_03(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    bayraklar = [ad for ad, cevap in n.items() if ad != "ekonomik_gerekce_var" and cevap.noul > 0.7]
    if n["ekonomik_gerekce_var"].noul < 0.3:
        bayraklar.append("ekonomik_gerekce_yok")
    skor = s["sib_gerekcesi"].score
    satirlar = [
        f"Tipoloji: {c['tipoloji'].choice} (güven {c['tipoloji'].confidence:.2f}) | "
        f"ŞİB gerekçesi: {skor:.2f} | Bayraklar: {', '.join(bayraklar) or '-'}"
    ]

    if skor >= 1.6 and c["tipoloji"].choice != "olagan":
        satirlar.append("Karar: ŞİB adayı — 10 gün içinde MASAK bildirimi değerlendir, hesabı kısıtla.")
    elif skor >= 1.0 or c["tipoloji"].confidence < 0.6:
        satirlar.append("Karar: belge talebi — müşteriden kaynak beyanı iste, 5 iş günü takip.")
    else:
        satirlar.append("Karar: izlemede bırak — 30 gün sonra tekrar tara.")

    satirlar.append("Not: aynı soru setini diğer iki kayıtla denemek için jev/playground/03_*.state_2/3.json dosyalarını yükle.")
    return satirlar


# ==============================================================================================
# 04 — KOBİ kredi başvurusu ön değerlendirme
# ==============================================================================================
S04_TALEP = 3_000_000.0
S04_FINANSAL = {
    "net_satis_tl": 41_200_000,
    "faaliyet_kari_tl": 3_050_000,
    "faiz_amortisman_oncesi_kar_tl": 4_100_000,
    "toplam_finansal_borc_tl": 9_800_000,
    "ozkaynak_tl": 5_200_000,
    "yillik_borc_servisi_tl": 3_400_000,
    "stok_devir_gun": 118,
    "alacak_tahsil_gun": 96,
}

S04_STATE = {
    "firma": {
        "unvan": "ÖRNEK MAKİNA SAN. TİC. LTD. ŞTİ.",
        "sektor": "metal_isleme",
        "faaliyet_yili": 14,
        "calisan": 38,
        "kredi_notu": 1_240,
    },
    "talep": {"urun": "isletme_kredisi", "tutar_tl": S04_TALEP, "vade_ay": 36, "teminat": "ipotek_2_derece"},
    "finansal": S04_FINANSAL,
    "sube_notu": (
        "Firma sahibiyle görüşüldü. Son iki yıl ciro büyümesi güçlü ancak büyümenin tamamı "
        "tek bir otomotiv yan sanayi müşterisinden geliyor; bu müşteriden alacak vadesi "
        "90 günü aşmış durumda. Ortak, 'yeni CNC tezgâhı alacağız, ödemesini peşin yapacağız' "
        "dedi, ancak talep işletme kredisi olarak açıldı. Geçen yıl iki çek karşılıksız çıkmış, "
        "aynı gün kapatılmış. Bilanço 2025 yıl sonu; 2026 ara dönem verisi henüz verilmedi. "
        "Ortakların başka bir firmada da ortaklığı olduğu söylendi, detay paylaşılmadı."
    ),
}

S04_SORULAR = _sorular(
    amac_tutarsiz=Noul(
        instructions="The stated use of the loan contradicts the product the application was opened under.",
        criteria={
            "true": "The borrower describes an investment or asset purchase while the application is for working capital, or vice versa.",
            "false": "The described use matches the requested product.",
        },
    ),
    musteri_yogunlasmasi=Noul(
        instructions="The company's revenue depends heavily on a single customer or a very small number of customers.",
    ),
    belge_eksik=Noul(
        instructions="Required financial or ownership documents are described as missing, outdated or not provided.",
    ),
    gizlenen_iliski=Noul(
        instructions="There are related parties or affiliated companies whose details the borrower avoided sharing.",
    ),
    odeme_disiplini_sorunu=Noul(
        instructions="The record mentions past payment failures such as bounced cheques, arrears or restructured debt.",
    ),
    kredi_amaci=Choice(
        instructions="What is the loan really going to be used for, based on the branch note?",
        criteria={
            "isletme_sermayesi": "Day-to-day working capital: stock, payroll, supplier payments.",
            "yatirim": "Buying machinery, property or other fixed assets.",
            "borc_kapatma": "Repaying or refinancing existing debt.",
            "alacak_finansmani": "Bridging receivables that customers have not yet paid.",
            "belirsiz": "The purpose cannot be determined from the file.",
        },
    ),
    dosya_kalitesi=Score(
        instructions="How ready is this credit file for a decision without further information?",
        criteria=[
            "Not ready: key documents or explanations are missing.",
            "Partly ready: decision possible but conditions or extra documents are needed.",
            "Ready: file is complete and internally consistent.",
        ],
    ),
)


def karar_04(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    borc_ozkaynak = S04_FINANSAL["toplam_finansal_borc_tl"] / S04_FINANSAL["ozkaynak_tl"]
    dscr = S04_FINANSAL["faiz_amortisman_oncesi_kar_tl"] / S04_FINANSAL["yillik_borc_servisi_tl"]
    nakit_dongusu = S04_FINANSAL["stok_devir_gun"] + S04_FINANSAL["alacak_tahsil_gun"]

    satirlar = [
        f"Borç/Özkaynak: {borc_ozkaynak:.2f} (limit 2.00) | DSCR: {dscr:.2f} (limit 1.25) | "
        f"Nakit döngüsü: {nakit_dongusu} gün",
        f"Talep: {S04_TALEP:,.0f} TL | Algılanan amaç: {c['kredi_amaci'].choice} "
        f"(güven {c['kredi_amaci'].confidence:.2f})",
    ]

    kirmizi = []
    if borc_ozkaynak > 2.0:
        kirmizi.append("borç/özkaynak limit üstü")
    if dscr < 1.25:
        kirmizi.append("borç servisi karşılama yetersiz")
    if n["musteri_yogunlasmasi"].noul > 0.7:
        kirmizi.append("tek müşteri yoğunlaşması")
    if n["gizlenen_iliski"].noul > 0.6:
        kirmizi.append("beyan edilmeyen ilişkili taraf")
    if n["odeme_disiplini_sorunu"].noul > 0.6:
        kirmizi.append("geçmiş ödeme disiplini")

    if n["belge_eksik"].noul > 0.6 or s["dosya_kalitesi"].score < 0.8:
        satirlar.append("Karar: DOSYA EKSİK. Ara dönem bilanço + ortaklık yapısı istensin, tahsise gönderilmesin.")
    elif n["amac_tutarsiz"].noul > 0.7:
        satirlar.append(
            f"Karar: ÜRÜN DEĞİŞİKLİĞİ. Talep {c['kredi_amaci'].choice} görünüyor; "
            "yatırım kredisi olarak yeniden yapılandırılsın."
        )
    elif len(kirmizi) >= 3:
        satirlar.append("Karar: ÜST YETKİ. Genel müdürlük kredi komitesine, teminat güçlendirme şartı ile.")
    elif kirmizi:
        satirlar.append("Karar: ŞARTLI ÖN ONAY. Bölge kredi tahsise; ipotek 1. dereceye alınması şartı eklensin.")
    else:
        satirlar.append("Karar: STANDART AKIŞ. Şube yetkisinde tahsis sürecine girsin.")

    satirlar.append(f"Kırmızı bayraklar: {', '.join(kirmizi) if kirmizi else '-'}")
    return satirlar


# ==============================================================================================
# 05 — Ticari kredi erken uyarı / IFRS 9 aşama önerisi
# ==============================================================================================
S05_GECIKME_GUN = 24
S05_LIMIT_KULLANIM = 0.97
S05_BAKIYE = 47_500_000.0

S05_STATE = {
    "firma": {"unvan": "ANADOLU TEKSTIL A.S.", "sektor": "hazir_giyim_ihracat", "risk_bakiyesi_tl": S05_BAKIYE},
    "sayisal_sinyaller": {
        "nakdi_limit_kullanim_orani": S05_LIMIT_KULLANIM,
        "en_uzun_gecikme_gun": S05_GECIKME_GUN,
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

S05_SORULAR = _sorular(
    temerrut_yakin=Noul(
        instructions=(
            "Taken together, the signals indicate that the borrower is unlikely to pay its credit "
            "obligations in full without the bank realising collateral or granting relief."
        ),
    ),
    yapisal_bozulma=Noul(
        instructions="The deterioration looks structural rather than a temporary liquidity squeeze.",
        criteria={
            "true": "The borrower's business model, main market or capacity is impaired in a lasting way.",
            "false": "The problem is timing of cash flows and the underlying business is intact.",
        },
    ),
    baska_bankada_yapilandirma=Noul(
        instructions="The borrower has restructured or extended debt with another creditor because of financial difficulty.",
    ),
    yonetim_zayifligi=Noul(
        instructions="There are governance or management stability problems at the borrower.",
    ),
    beyan_dogrulanabilir=Noul(
        instructions="The borrower's recovery claims are backed by verifiable evidence.",
        criteria={
            "true": "Contracts, orders or documents supporting the recovery plan were actually shown.",
            "false": "The recovery plan rests on statements only, with no document produced.",
        },
    ),
    ana_risk=Choice(
        instructions="What is the dominant driver of risk in this file?",
        criteria={
            "alici_yogunlasmasi": "Loss or distress of a dominant buyer.",
            "sektorel_daralma": "Sector-wide contraction in demand or margins.",
            "likidite": "Cash-flow timing problems with an otherwise sound business.",
            "yonetim": "Management or governance failure.",
            "asiri_borcluluk": "Debt load too large for the business to service.",
        },
    ),
    izleme_siddeti=Score(
        instructions="How closely should this exposure be monitored from now on?",
        criteria=[
            "Standard: no change in monitoring.",
            "Close watch: quarterly review, tighter limits, collateral review.",
            "Intensive: monthly review, no new limits, exit or restructuring plan required.",
        ],
    ),
)


def karar_05(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    kantitatif = S05_GECIKME_GUN >= 30 or S05_LIMIT_KULLANIM >= 1.0
    nitel = (
        n["temerrut_yakin"].noul > 0.6
        or (n["yapisal_bozulma"].noul > 0.6 and s["izleme_siddeti"].score >= 1.5)
        or n["baska_bankada_yapilandirma"].noul > 0.7
    )
    satirlar = [
        f"Risk bakiyesi: {S05_BAKIYE:,.0f} TL | Gecikme: {S05_GECIKME_GUN} gün | "
        f"Limit kullanım: {S05_LIMIT_KULLANIM:.0%} | Teminat kapsama: 62%",
        f"Kantitatif tetik: {'var' if kantitatif else 'yok'} | Nitel tetik: {'var' if nitel else 'yok'}",
    ]

    if n["temerrut_yakin"].noul > 0.8 and n["yapisal_bozulma"].noul > 0.7:
        satirlar += [
            "Öneri: 3. AŞAMA değerlendirmesi (temerrüt karinesi). Tahsilat ve teminat birimi devreye alınsın.",
            "Aksiyon: yeni limit tahsisi durdurulsun, mevcut riskin teminatlandırılması için 15 gün süre.",
        ]
    elif kantitatif or nitel:
        satirlar += [
            "Öneri: 2. AŞAMA — yakın izleme. Ömür boyu beklenen zarar karşılığına geçiş önerilir.",
            "Aksiyon: aylık nakit akım tablosu istensin, limitler dondurulsun, teminat güncellemesi yapılsın.",
        ]
    else:
        satirlar.append("Öneri: 1. AŞAMA devam. Standart izleme, çeyreklik gözden geçirme.")

    if n["beyan_dogrulanabilir"].noul < 0.4:
        satirlar.append("Not: iyileşme beyanı belgesiz. Yeni alıcı sözleşmesi ibraz edilmeden limit artışı değerlendirilmesin.")
    if c["ana_risk"].confidence < 0.6:
        satirlar.append("Not: ana risk sürücüsü belirsiz — dosya kredi izleme uzmanına yazılı görüş için gönderilsin.")
    return satirlar


# ==============================================================================================
# 06 — Tahsilat görüşmesi değerlendirmesi
# ==============================================================================================
S06_GECIKME_GUN = 92
S06_BORC = 74_300.0

S06_STATE = {
    "dosya": {"urun": "ihtiyac_kredisi", "gecikme_gun": S06_GECIKME_GUN, "bakiye_tl": S06_BORC, "onceki_vaat_sayisi": 2},
    "gorusme_dokumu": [
        {"taraf": "temsilci", "metin": "İyi günler, 74.300 TL gecikmiş borcunuz için arıyorum. Bugün ödeme yapabilecek misiniz?"},
        {"taraf": "musteri", "metin": "Eşim altı ay önce vefat etti, tek gelir bendim, şubatta da işten çıkarıldım. Şu an işsizlik maaşı alıyorum, 14 bin lira."},
        {"taraf": "temsilci", "metin": "Anlıyorum ama bu borç sizin sorumluluğunuzda. Ödemezseniz icra takibi başlar, evinize haciz gelir."},
        {"taraf": "musteri", "metin": "Biliyorum, kaçmıyorum. Ayda 3 bin lira ödeyebilirim, daha fazlasına gücüm yetmez. Doktor raporum da var, depresyon tedavisi görüyorum."},
        {"taraf": "temsilci", "metin": "3 bin lira olmaz, en az 10 bin lira ödemeniz gerekiyor, yoksa dosyayı avukata devrederim. Akrabalarınızdan borç alın."},
        {"taraf": "musteri", "metin": "Bu ay 3 bin lirayı 28'inde yatırırım, söz veriyorum. Gerisi için yapılandırma istiyorum."},
    ],
}

S06_SORULAR = _sorular(
    odeme_vaadi=Noul(
        instructions="The customer commits to a specific payment amount on a specific date.",
        criteria={
            "true": "A concrete amount and a date are stated by the customer.",
            "false": "The customer makes no concrete commitment, or only says they will 'try'.",
        },
    ),
    mali_zorluk_beyani=Noul(
        instructions="The customer states a genuine change in circumstances that reduced their ability to pay.",
        criteria={
            "true": "Job loss, illness, bereavement, disability or a similar event is described.",
            "false": "No such event is described; the customer simply refuses or avoids payment.",
        },
    ),
    hassas_musteri=Noul(
        instructions=(
            "The customer shows signs of vulnerability that require special care: bereavement, "
            "serious illness, mental health treatment, disability or sole reliance on state benefits."
        ),
    ),
    odeme_niyeti_yok=Noul(
        instructions="The customer shows no intention to pay and avoids engaging with the debt.",
    ),
    uygunsuz_tahsilat_dili=Noul(
        instructions=(
            "The collections agent used pressure, threats, or improper instructions that a regulator "
            "would treat as unfair debt collection practice."
        ),
        criteria={
            "true": "Threats beyond the bank's actual legal rights, shaming, or telling the customer to borrow from family or third parties.",
            "false": "The agent stayed factual and respectful about consequences.",
        },
    ),
    sonraki_adim=Choice(
        instructions="What should the bank do next with this file?",
        criteria={
            "yapilandirma_teklifi": "Offer a restructuring or payment plan matched to the customer's capacity.",
            "odemesiz_donem": "Grant a temporary payment holiday because of hardship.",
            "vaadi_takip": "Record the promise to pay and follow up on the promised date.",
            "hukuki_takip": "Move the file to legal enforcement.",
            "sosyal_destek_yonlendirme": "Pause collection and refer to the bank's vulnerable-customer process.",
        },
    ),
    tahsil_edilebilirlik=Score(
        instructions="How likely is this debt to be recovered through voluntary payment over the next 12 months?",
        criteria=[
            "Unlikely: no capacity and no intent.",
            "Partial: some capacity, recovery only with a long, reduced plan.",
            "Likely: capacity and intent are both present.",
        ],
    ),
)


def karar_06(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    onerilen_taksit = 3_000.0
    satirlar = [
        f"Gecikme: {S06_GECIKME_GUN} gün | Bakiye: {S06_BORC:,.0f} TL | "
        f"Beyan edilen taksitle kapanış: ~{S06_BORC / onerilen_taksit:.0f} ay",
        f"Önerilen adım: {c['sonraki_adim'].choice} (güven {c['sonraki_adim'].confidence:.2f}) | "
        f"Tahsil edilebilirlik: {s['tahsil_edilebilirlik'].score:.2f}",
    ]

    if n["uygunsuz_tahsilat_dili"].noul > 0.6:
        satirlar += [
            "UYARI: tahsilat dili uygunsuz. Çağrı kaydı uyum birimine gönderilsin, temsilciye geri bildirim.",
            "Aksiyon: müşteri farklı bir temsilci tarafından yeniden aransın; bu görüşmedeki vaat baskı altında sayılsın.",
        ]

    if n["hassas_musteri"].noul > 0.7 and n["mali_zorluk_beyani"].noul > 0.6:
        satirlar += [
            "Karar: HASSAS MÜŞTERİ protokolü. Hukuki takip 90 gün durdurulsun.",
            "Aksiyon: sağlık raporu + işsizlik ödeneği belgesi istensin, ödemesiz dönem + vade uzatımı teklif edilsin.",
        ]
    elif n["odeme_niyeti_yok"].noul > 0.7 and s["tahsil_edilebilirlik"].score < 0.7:
        satirlar.append("Karar: hukuki takip hazırlığı. Dosya avukata, teminat ve mal varlığı araştırması başlasın.")
    elif s["tahsil_edilebilirlik"].score >= 1.4:
        satirlar.append("Karar: yapılandırma teklifi. Vade uzatımı ile taksit ödeme gücüne çekilsin.")
    else:
        satirlar.append("Karar: kısmi tahsilat planı. Düşük taksitli 36 ay + dönemsel gözden geçirme.")

    if n["odeme_vaadi"].noul > 0.7:
        satirlar.append("Aksiyon: ödeme vaadi kaydedilsin (28'i), vaat günü +1 hatırlatma araması planlansın.")
        if S06_STATE["dosya"]["onceki_vaat_sayisi"] >= 2:
            satirlar.append("Not: üçüncü vaat — tek başına vaat takibi yeterli değil, yazılı plan şart.")
    return satirlar


# ==============================================================================================
# 07 — SIM swap / hesap ele geçirme triyajı
# ==============================================================================================
S07_STATE = {
    "telemetri": {
        "son_giris": {"cihaz": "yeni_cihaz", "cihaz_yasi_saat": 3, "ip_ulke": "TR", "ip_asn": "mobil_operator"},
        "son_1_saatte": [
            "sifre degisikligi",
            "telefon numarasi guncelleme denemesi (basarisiz)",
            "gunluk transfer limiti 10.000 -> 250.000 TL yukseltildi",
            "yeni IBAN tanimlandi",
            "e-posta adresi degistirildi",
        ],
        "sms_otp": "son 40 dakikada 6 OTP gonderildi, 5'i dogru girildi",
        "musteri_kayitli_cihaz_sayisi": 2,
    },
    "arayan_beyani": (
        "Sabahtan beri telefonum şebeke bulmuyor, 'SIM kart yok' yazıyor. Operatörü aradım, "
        "hattımın dün akşam başka bir yerde yeniden düzenlendiğini söylediler, ben talep etmedim. "
        "Uygulamaya girmeye çalışıyorum, şifrem çalışmıyor. E-postama da giremiyorum. "
        "Hesabımda 260 bin lira var, lütfen hemen durdurun."
    ),
}

S07_SORULAR = _sorular(
    sim_swap_belirtisi=Noul(
        instructions=(
            "The caller describes losing mobile network service in a way consistent with their SIM "
            "being ported or re-issued without their request."
        ),
    ),
    ele_gecirme_suruyor=Noul(
        instructions=(
            "The recorded account events indicate an attacker is currently in control of the account "
            "and preparing to move money."
        ),
        criteria={
            "true": "Credential, contact-detail, limit or payee changes cluster together in a short window.",
            "false": "The events look like ordinary self-service activity by the customer.",
        },
    ),
    arayan_supheli=Noul(
        instructions="There is reason to doubt that the caller is the genuine customer.",
        criteria={
            "true": "The caller's account is inconsistent, evasive, or fits a social-engineering attempt against the call centre.",
            "false": "The caller's account is coherent and matches the recorded events.",
        },
    ),
    teknik_ariza=Noul(
        instructions="The symptoms are explained by an ordinary technical fault rather than an attack.",
    ),
    olay_tipi=Choice(
        instructions="What is happening on this account?",
        criteria={
            "sim_swap_ato": "SIM swap used to take over the account.",
            "kimlik_avi_ato": "Credentials harvested by phishing and now used by an attacker.",
            "zararli_yazilim": "Device malware or a remote-access tool driving the session.",
            "yetkili_kisi": "A family member or acquaintance with legitimate access made the changes.",
            "teknik_sorun": "No attack: app, SIM or network fault.",
        },
    ),
    mudahale_aciliyeti=Score(
        instructions="How fast must the bank act?",
        criteria=[
            "Routine: can be handled in the normal support queue.",
            "Same day: act within hours to prevent loss.",
            "Immediate: money is at imminent risk; act within minutes.",
        ],
    ),
)


def karar_07(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    saldiri = c["olay_tipi"].choice in {"sim_swap_ato", "kimlik_avi_ato", "zararli_yazilim"}
    acil = s["mudahale_aciliyeti"].score >= 1.5
    satirlar = [
        f"Olay tipi: {c['olay_tipi'].choice} (güven {c['olay_tipi'].confidence:.2f}) | "
        f"Aciliyet: {s['mudahale_aciliyeti'].score:.2f}"
    ]

    if n["ele_gecirme_suruyor"].noul > 0.7 and acil:
        satirlar += [
            "Karar: ACİL KISIT. Tüm dijital kanallar kapatılsın, giden ödemeler durdurulsun, aktif oturumlar sonlandırılsın.",
            "Aksiyon: son 1 saatte tanımlanan IBAN ve limit artışı geri alınsın.",
            "Aksiyon: SIM değişikliği sonrası 72 saat OTP ile işlem yapılmasın (numara bazlı kısıt).",
        ]
    elif saldiri:
        satirlar.append("Karar: hesabı izlemeye al, yüksek tutarlı işlemler için ikinci kanal teyidi zorunlu olsun.")
    elif n["teknik_ariza"].noul > 0.7:
        satirlar.append("Karar: teknik destek kuyruğu. Kısıt uygulanmasın, cihaz kaydı yenilensin.")
    else:
        satirlar.append("Karar: belirsiz. Fraud ekibi dosyayı incelesin, geçici olarak transfer limiti düşürülsün.")

    if n["arayan_supheli"].noul > 0.5:
        satirlar.append(
            "Not: arayanın kimliği şüpheli. Telefonda işlem yapılmasın; şube + kimlik ibrazı ile "
            "yeniden kimliklendirme istensin."
        )
    else:
        satirlar.append("Not: arayan beyanı telemetri ile tutarlı. Geri arama kayıtlı sabit numaradan yapılsın.")

    if n["sim_swap_belirtisi"].noul > 0.7:
        satirlar.append("Aksiyon: operatörden hat değişiklik tarihi yazılı istensin — sonraki itiraz/dava dosyasında gerekiyor.")
    return satirlar


# ==============================================================================================
# 08 — Bireysel kredi yapılandırma talebi
# ==============================================================================================
S08_DOSYA = {
    "urun": "konut_kredisi",
    "kalan_anapara_tl": 1_240_000,
    "kalan_vade_ay": 84,
    "aylik_taksit_tl": 21_800,
    "beyan_gelir_tl": 46_000,
    "gecikme_gun": 0,
    "onceki_yapilandirma": False,
}

S08_STATE = {
    "dosya": S08_DOSYA,
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

S08_SORULAR = _sorular(
    yapilandirma_talebi=Noul(
        instructions="The message asks the bank to change the terms of an existing loan.",
    ),
    gecici_zorluk=Noul(
        instructions="The difficulty described is temporary with a foreseeable end, rather than permanent.",
        criteria={
            "true": "The customer names a limited period or an expected recovery (reduced hours, short-term leave, seasonal drop).",
            "false": "The income loss looks permanent or open-ended.",
        },
    ),
    proaktif_basvuru=Noul(
        instructions="The customer is reaching out before missing a payment rather than after falling behind.",
    ),
    sikayet_tonu=Noul(
        instructions="The message contains a complaint about how the bank or a branch handled the customer.",
    ),
    regulator_tehdidi=Noul(
        instructions="The customer threatens to escalate to a regulator, ombudsman, consumer arbitration or the press.",
    ),
    istenen_cozum=Choice(
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
    odeme_kapasitesi=Score(
        instructions="How much of the current instalment can this customer sustain during the difficulty?",
        criteria=[
            "Almost none: needs a full payment holiday.",
            "Partial: can pay a reduced instalment.",
            "Most of it: a small adjustment is enough.",
        ],
    ),
)

S08_URUN_KURALI: dict[str, Callable[[dict[str, Any]], bool]] = {
    "vade_uzatimi": lambda d: d["kalan_vade_ay"] <= 96,
    "odemesiz_donem": lambda d: d["gecikme_gun"] == 0 and not d["onceki_yapilandirma"],
    "sadece_faiz": lambda d: d["kalan_anapara_tl"] >= 250_000,
    "faiz_indirimi": lambda d: False,          # bireysel konutta fiyat degisikligi yetkisi tahsiste
    "tam_kapatma_indirimi": lambda d: False,   # sadece takipteki dosyalarda
    "bilgi_talebi": lambda d: True,
}


def karar_08(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    talep = c["istenen_cozum"].choice
    uygun = S08_URUN_KURALI.get(talep, lambda d: False)(S08_DOSYA)
    taksit_gelir = S08_DOSYA["aylik_taksit_tl"] / S08_DOSYA["beyan_gelir_tl"]
    dusuk_gelirle = S08_DOSYA["aylik_taksit_tl"] / (S08_DOSYA["beyan_gelir_tl"] * 0.40)

    satirlar = [
        f"Talep: {talep} (güven {c['istenen_cozum'].confidence:.2f}) | Ürün uygun mu: {'evet' if uygun else 'hayır'}",
        f"Taksit/gelir: normalde {taksit_gelir:.0%}, kısa çalışmada {dusuk_gelirle:.0%}",
    ]

    if n["yapilandirma_talebi"].noul < 0.5:
        satirlar.append("Karar: yapılandırma talebi değil. Bilgilendirme yanıtı, standart SLA.")
    elif c["istenen_cozum"].confidence < 0.55:
        satirlar.append("Karar: talep belirsiz. Müşteri aransın, tercih netleştirilsin.")
    elif n["gecici_zorluk"].noul > 0.6 and s["odeme_kapasitesi"].score >= 1.0 and uygun:
        satirlar.append(f"Karar: {talep} teklif edilsin. 6 ay indirimli taksit + sonrasında orijinal plana dönüş.")
    elif n["gecici_zorluk"].noul > 0.6 and s["odeme_kapasitesi"].score < 1.0:
        satirlar.append("Karar: 3 ay ödemesiz dönem + vade uzatımı kombinasyonu; kısa çalışma belgesi istensin.")
    elif not uygun:
        satirlar.append(f"Karar: talep edilen ürün ({talep}) bu dosyaya uygun değil. Alternatif olarak vade uzatımı teklif edilsin.")
    else:
        satirlar.append("Karar: kalıcı gelir kaybı ihtimali. Gelir belgesi + detaylı bütçe çalışması ile tahsise gönderilsin.")

    if n["proaktif_basvuru"].noul > 0.7:
        satirlar.append("Not: gecikmesiz proaktif başvuru. 'Önce gecikmeye düş' yanlış yönlendirmesi düzeltilsin, sicil korunur.")
    if n["sikayet_tonu"].noul > 0.6:
        satirlar.append("Aksiyon: şube yönlendirmesi hakkında şikâyet kaydı açılsın, bölge müdürlüğüne geri bildirim.")
    if n["regulator_tehdidi"].noul > 0.6:
        satirlar.append("Aksiyon: BDDK/THH eskalasyon riski — yanıt 3 iş günü içinde ve yazılı gerekçeli verilsin.")
    return satirlar


# ==============================================================================================
# 09 — Uzaktan kimlik tespiti / KYC değerlendirmesi
# ==============================================================================================
S09_STATE = {
    "basvuru": {
        "musteri_tipi": "gercek_kisi",
        "yas": 24,
        "beyan_meslek": "ithalat_ihracat_danismani",
        "beyan_aylik_gelir_tl": 180_000,
        "beyan_islem_hacmi_tl_ay": 2_500_000,
        "beyan_ulkeler": ["TR", "AE", "RU"],
        "adres_belgesi": "3 ay once duzenlenmis fatura, farkli isim uzerine",
    },
    "cihaz": {
        "yeni_cihaz": True,
        "ip_vpn": True,
        "ayni_cihazdan_onceki_basvuru_sayisi": 2,
        "ekran_paylasimi_tespiti": "aktif",
    },
    "video_tutanagi": (
        "Görüşme 6 dakika sürdü. Müşteri ekranını başka bir uygulamada paylaşıyordu; "
        "sorulara cevap vermeden önce her seferinde 2-3 saniye duraksadı ve kamera dışından "
        "gelen bir sesi dinlediği izlenimi verdi. 'Aylık işlem hacminiz neden bu kadar yüksek?' "
        "sorusuna 'ailemin şirketi var, detayını bilmiyorum, öyle yazmamı söylediler' dedi. "
        "Kimlik belgesindeki hologram açı değiştiğinde kaybolmadı. Müşteri, hesabın kartını "
        "kimin kullanacağı sorulduğunda 'ben kullanacağım' dedi ama kart teslim adresi olarak "
        "başka bir ildeki iş yerini verdi. Devlet görevinde olup olmadığı sorulduğunda "
        "'babam belediyede müdürdü, emekli oldu' bilgisini kendiliğinden paylaştı."
    ),
}

S09_SORULAR = _sorular(
    baskasi_adina_hesap=Noul(
        instructions="The account appears to be opened for someone else's use rather than the applicant's own.",
        criteria={
            "true": "The applicant is prompted by a third party, does not know their own declared details, or the card/access is destined for another person.",
            "false": "The applicant clearly opens and will use the account themselves.",
        },
    ),
    yonlendirilme_belirtisi=Noul(
        instructions="During the video call the applicant appears to be coached or read answers supplied by someone else.",
    ),
    belge_supheli=Noul(
        instructions="The identity or address documents show signs of tampering or do not belong to the applicant.",
    ),
    beyan_profil_uyumsuz=Noul(
        instructions=(
            "The declared income and transaction volume are inconsistent with the applicant's age, "
            "occupation and stated circumstances."
        ),
    ),
    pep_baglantisi=Noul(
        instructions="The applicant is, or is a close associate or family member of, a politically exposed person.",
        criteria={
            "true": "The applicant or a close relative holds or held a prominent public function.",
            "false": "No connection to a public function is described.",
        },
    ),
    red_gerekcesi=Choice(
        instructions="If this application cannot be completed as-is, what is the main reason?",
        criteria={
            "kimlik_supheli": "Doubt about who the applicant is.",
            "para_katiri_supheli": "The account is likely to be used as a mule account.",
            "belge_eksik": "Documents are missing or invalid but the applicant seems genuine.",
            "yuksek_risk_profil": "Genuine applicant, but the risk profile needs enhanced due diligence.",
            "engel_yok": "Nothing blocks completion.",
        },
    ),
    musteri_riski=Score(
        instructions="What customer risk rating does this application deserve?",
        criteria=[
            "Low: simplified due diligence is sufficient.",
            "Standard: normal due diligence.",
            "High: enhanced due diligence, senior approval and ongoing monitoring required.",
        ],
    ),
)


def karar_09(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    risk = s["musteri_riski"].score
    satirlar = [
        f"Red gerekçesi: {c['red_gerekcesi'].choice} (güven {c['red_gerekcesi'].confidence:.2f}) | "
        f"Müşteri riski: {risk:.2f}"
    ]

    if n["belge_supheli"].noul > 0.6 or n["baskasi_adina_hesap"].noul > 0.7:
        satirlar += [
            "Karar: BAŞVURU REDDİ. Uzaktan kimlik tespiti tamamlanmasın, görüşme kaydı saklansın.",
            "Aksiyon: cihaz/IP kara listeye, aynı cihazdan yapılan önceki 2 başvuru geriye dönük incelensin.",
            "Aksiyon: para katırı şüphesi uyum birimine bildirilsin.",
        ]
    elif n["yonlendirilme_belirtisi"].noul > 0.6:
        satirlar.append("Karar: görüşme sonlandırılsın, müşteri şube kanalıyla yüz yüze kimlik tespitine yönlendirilsin.")
    elif risk >= 1.6 or n["beyan_profil_uyumsuz"].noul > 0.7:
        satirlar += [
            "Karar: SIKILAŞTIRILMIŞ TEDBİR ile aç. Başlangıç limitleri düşük (günlük 25.000 TL), kart teslimi adrese kısıtlı.",
            "Aksiyon: gelir ve fon kaynağı belgesi 30 gün içinde istensin, alınmazsa hesap kısıtlansın.",
        ]
    elif c["red_gerekcesi"].choice == "belge_eksik":
        satirlar.append("Karar: eksik belge tamamlansın (adres belgesi başvuru sahibi adına olmalı), sonra tekrar değerlendir.")
    else:
        satirlar.append("Karar: standart müşteri edinimi. Normal limitler.")

    if n["pep_baglantisi"].noul > 0.5:
        satirlar.append(
            "Not: PEP/PEP yakını beyanı var. Hesap açılışı üst düzey yönetici onayına bağlansın, "
            "fon kaynağı yazılı alınsın, sürekli izleme açılsın."
        )
    satirlar.append("Not: görüşme sırasında ekran paylaşımı aktifti — tek başına red sebebi, teknik kontrol kaydı tutulsun.")
    return satirlar


# ==============================================================================================
# 10 — Gişede yüksek tutarlı nakit çekim
# ==============================================================================================
S10_TUTAR = 350_000.0

S10_STATE = {
    "musteri": {"yas": 75, "sube_musterisi_yil": 22, "son_1_yil_nakit_cekim_ortalama_tl": 12_000},
    "islem": {"tip": "nakit_cekim", "tutar_tl": S10_TUTAR, "vadeli_hesap_bozuldu": True, "faiz_kaybi_tl": 41_000},
    "gise_notu": (
        "Müşteri yanında 40'lı yaşlarda bir erkekle geldi. Tutarı soran gişe görevlisine "
        "önce yanındaki kişi cevap verdi. Müşteriye parayı ne için çektiğini sorduğumuzda "
        "'evi tadilat yaptıracağım, usta nakit istiyor' dedi ama tadilat yapacak firmanın "
        "adını söyleyemedi. Vadeli hesabını bozmanın 41.000 TL faiz kaybı doğuracağını "
        "açıkladığımızda tereddüt etti, yanındaki kişi 'nasıl olsa geri yatıracağız' dedi. "
        "Müşteri telefonuna sürekli mesaj geliyordu ve her mesajdan sonra yanındaki kişiye "
        "bakıyordu. Ayrıca 'bankadan aradılar, hesabım güvenli değilmiş, parayı çekip "
        "güvenli hesaba yatıracakmışım' cümlesini bir kez kurdu, sonra konuyu değiştirdi. "
        "Müşteri daha önce hiç bu tutarda nakit çekmedi."
    ),
}

S10_SORULAR = _sorular(
    baski_altinda=Noul(
        instructions="The customer appears to be acting under pressure or direction from the person accompanying them.",
        criteria={
            "true": "The companion answers for the customer, corrects them, or the customer looks to them before responding.",
            "false": "The customer speaks and decides for themselves.",
        },
    ),
    gerekce_tutarsiz=Noul(
        instructions="The stated reason for the withdrawal does not hold up under simple questioning.",
    ),
    banka_gorevlisi_taklidi=Noul(
        instructions=(
            "The customer repeats the claim that the bank or an official told them to move money to a "
            "'safe account', a classic impersonation scam."
        ),
    ),
    yakin_istismari=Noul(
        instructions="The situation fits financial abuse of an older person by a relative, carer or acquaintance.",
    ),
    kendi_iradesi=Noul(
        instructions="The customer understands the transaction and its cost and genuinely wants it.",
        criteria={
            "true": "The customer explains the purpose consistently and accepts the cost knowingly.",
            "false": "The customer is confused about the purpose or unaware of what they are giving up.",
        },
    ),
    durum=Choice(
        instructions="What best describes this counter request?",
        criteria={
            "guvenli_hesap_dolandiriciligi": "Impersonation scam telling the customer to move money for safety.",
            "yakin_istismari": "Financial abuse by a family member, carer or acquaintance.",
            "ucuncu_kisi_yonlendirmesi": "The customer is being directed by someone they met recently.",
            "mesru_ihtiyac": "A genuine personal need for cash.",
            "belirsiz": "There is not enough in the note to tell.",
        },
    ),
    mudahale_gerekliligi=Score(
        instructions="How strongly should the branch intervene before releasing the cash?",
        criteria=[
            "None: complete the transaction normally.",
            "Speak privately: separate the customer from the companion and ask again.",
            "Withhold: delay the transaction and escalate before any cash leaves.",
        ],
    ),
)


def karar_10(y: SystemOneResponse) -> list[str]:
    n, c, s = y.nouls, y.choices, y.scores
    ortalama = S10_STATE["musteri"]["son_1_yil_nakit_cekim_ortalama_tl"]
    korunmasiz = S10_STATE["musteri"]["yas"] >= 70
    olagan_disi = S10_TUTAR >= 10 * ortalama
    mudahale = s["mudahale_gerekliligi"].score

    satirlar = [
        f"Tutar: {S10_TUTAR:,.0f} TL (ortalamanın {S10_TUTAR / ortalama:.0f} katı) | Faiz kaybı: 41.000 TL | "
        f"Durum: {c['durum'].choice} (güven {c['durum'].confidence:.2f})"
    ]

    if n["banka_gorevlisi_taklidi"].noul > 0.6:
        satirlar += [
            "Karar: İŞLEMİ TAMAMLAMA. 'Güvenli hesap' anlatısı banka görevlisi taklidi dolandırıcılığıdır.",
            "Aksiyon: müşteri ayrı bir odaya alınsın, refakatçi dışarıda kalsın, kolluk (155) bilgilendirilsin.",
        ]
    elif mudahale >= 1.5 and (n["baski_altinda"].noul > 0.6 or n["gerekce_tutarsiz"].noul > 0.6):
        satirlar += [
            "Karar: İŞLEMİ BEKLET. Nakit teslim edilmesin, şube müdürü ikinci görüşmeyi yapsın.",
            "Aksiyon: müşteri yalnız görüşülsün; kayıtlı yakın/temsilci aranarak teyit alınsın.",
        ]
    elif mudahale >= 0.8:
        satirlar.append("Karar: önce özel görüşme. Müşteri refakatçiden ayrı sorgulansın, sonra karar verilsin.")
    elif n["kendi_iradesi"].noul > 0.7 and c["durum"].choice == "mesru_ihtiyac":
        satirlar.append("Karar: işlem yapılsın. Faiz kaybı yazılı teyit alınarak nakit teslim edilsin.")
    else:
        satirlar.append("Karar: belirsiz. Şube müdürü onayına sunulsun, tutar bugün için düşürülmesi önerilsin.")

    if korunmasiz and (n["yakin_istismari"].noul > 0.5 or n["baski_altinda"].noul > 0.5):
        satirlar.append("Not: korunmasız müşteri istismarı şüphesi. Olay tutanağa bağlansın, kamera kaydı saklansın.")
    if olagan_disi:
        satirlar.append("Not: olağandışı nakit hareketi — MASAK değerlendirmesi için uyum birimine bilgi notu.")
    if n["kendi_iradesi"].noul < 0.4:
        satirlar.append("Not: müşteri işlemin sonucunu kavramamış olabilir; aydınlatma tekrarlansın, aceleye getirilmesin.")
    return satirlar


# ==============================================================================================
# Senaryo kayıt defteri
# ==============================================================================================
GOMULU_SENARYOLAR: list[Senaryo] = [
    Senaryo("01 — Kart itirazı / chargeback", "Ters ibraz açılsın mı, hangi gerekçe kodundan?", S01_STATE, S01_SORULAR, karar_01),
    Senaryo("02 — EFT/FAST dolandırıcılık", "İkna edilmiş müşteri ödemesi durdurulsun mu?", S02_STATE, S02_SORULAR, karar_02),
    Senaryo("03 — MASAK şüpheli işlem", "Hesap ŞİB adayı mı, analist ne yapsın?", S03_STATE, S03_SORULAR, karar_03),
    Senaryo("04 — KOBİ kredi ön değerlendirme", "Dosya tahsise gitsin mi, hangi yetkiye?", S04_STATE, S04_SORULAR, karar_04),
    Senaryo("05 — Erken uyarı / IFRS 9", "Kredi 2. aşamaya (yakın izleme) alınsın mı?", S05_STATE, S05_SORULAR, karar_05),
    Senaryo("06 — Tahsilat görüşmesi", "Yapılandırma mı, hukuki takip mi?", S06_STATE, S06_SORULAR, karar_06),
    Senaryo("07 — SIM swap / ele geçirme", "Kanallar kapatılsın mı?", S07_STATE, S07_SORULAR, karar_07),
    Senaryo("08 — Yapılandırma talebi", "Hangi çözüm ürünü teklif edilsin?", S08_STATE, S08_SORULAR, karar_08),
    Senaryo("09 — Uzaktan kimlik tespiti", "Hesap açılışı tamamlansın mı?", S09_STATE, S09_SORULAR, karar_09),
    Senaryo("10 — Gişede nakit çekim", "Nakit teslim edilsin mi?", S10_STATE, S10_SORULAR, karar_10),
]


# ==============================================================================================
# JSON talimat çözümleyici — yüklenen dosyanın biçimini kendisi algılar
# ==============================================================================================
SORU_TIPLERI = {"noul", "choice", "score"}


def soru_seti_mi(veri: Any) -> bool:
    """{"ad": {"type": "noul"|"choice"|"score", ...}} biçiminde mi?"""
    return (
        isinstance(veri, dict)
        and bool(veri)
        and all(isinstance(d, dict) and d.get("type") in SORU_TIPLERI for d in veri.values())
    )


def _tek_senaryo(veri: dict[str, Any], varsayilan_ad: str) -> list[Senaryo]:
    baslik = str(veri.get("baslik") or varsayilan_ad)
    aciklama = str(veri.get("aciklama") or "JSON talimattan yüklendi")
    sorular = veri.get("questions") or veri.get("sorular") or {}
    state = veri.get("state", veri.get("durum", {}))

    # Çoklu senaryo dosyamızda state bir dizi ise (03 toplu tarama) her kayıt ayrı senaryo olur.
    if isinstance(state, list) and state and all(isinstance(k, dict) for k in state):
        return [
            Senaryo(f"{baslik} ({i + 1}/{len(state)})", aciklama, kayit, sorular)
            for i, kayit in enumerate(state)
        ]
    return [Senaryo(baslik, aciklama, state, sorular)]


def talimat_coz(veri: Any, kaynak: str) -> list[Senaryo]:
    """Yüklenen JSON'u senaryo listesine çevirir. Desteklenen biçimler için modül docstring'ine bak."""
    if isinstance(veri, list):
        senaryolar: list[Senaryo] = []
        for i, oge in enumerate(veri):
            if isinstance(oge, dict) and ("questions" in oge or "sorular" in oge):
                senaryolar += _tek_senaryo(oge, f"{kaynak} #{i + 1}")
        if senaryolar:
            return senaryolar
        return [Senaryo(kaynak, "Yalnızca state yüklendi (dizi)", veri, {})]

    if not isinstance(veri, dict):
        return [Senaryo(kaynak, "Yalnızca state yüklendi", veri, {})]

    if "questions" in veri or "sorular" in veri:
        return _tek_senaryo(veri, kaynak)

    # {"ad": {"baslik", "state", "questions"}, ...} — tum_senaryolar.json biçimi
    if veri and all(isinstance(d, dict) and ("questions" in d or "sorular" in d) for d in veri.values()):
        senaryolar = []
        for ad, icerik in veri.items():
            senaryolar += _tek_senaryo(icerik, str(icerik.get("baslik") or ad))
        return senaryolar

    if soru_seti_mi(veri):
        return [Senaryo(kaynak, "Yalnızca soru seti yüklendi — state'i sen doldur", {}, veri)]

    return [Senaryo(kaynak, "Yalnızca state yüklendi", veri, {})]


# ==============================================================================================
# API çağrısını arayüzü kilitlemeden yapan işçi
# ==============================================================================================
class Isci(QtCore.QThread):
    """system_one çağrısını ayrı iş parçacığında yapar."""

    bitti = QtCore.pyqtSignal(object)
    hata = QtCore.pyqtSignal(str)

    def __init__(self, state: Any, sorular: dict[str, Any], api_key: str, proxy: str, model: str) -> None:
        super().__init__()
        self._state = state
        self._sorular = sorular
        self._api_key = api_key
        self._proxy = proxy
        self._model = model

    def run(self) -> None:  # pragma: no cover - arayuz akisi
        try:
            if self._proxy:
                os.environ["HTTPS_PROXY"] = self._proxy
            with TypeSafeClient(
                api_key=self._api_key or None, model=self._model or None, timeout=30
            ) as client:
                yanit = client.system_one(state=self._state, questions=self._sorular)
            self.bitti.emit(yanit)
        except TypeSafeAuthenticationError:
            self.hata.emit("API anahtarı reddedildi. Anahtar alanındaki değer doğru mu?")
        except TypeSafeRateLimitError as hata:
            self.hata.emit(f"Hız sınırı aşıldı, biraz bekleyip tekrar dene: {hata}")
        except TypeSafeAPITimeoutError as hata:
            self.hata.emit(f"İstek zaman aşımına uğradı: {hata}")
        except TypeSafeAPIConnectionError as hata:
            self.hata.emit(f"api.typesafe.ai'a bağlanılamadı (proxy/TLS?): {hata}")
        except TypeSafeError as hata:
            self.hata.emit(f"TypeSafe hatası: {hata}")
        except Exception as hata:  # beklenmeyen her sey de arayuzde gorunsun
            self.hata.emit(f"Beklenmeyen hata: {type(hata).__name__}: {hata}")


# ==============================================================================================
# Sonuç panosu için basit HTML üretimi
# ==============================================================================================
def _kacir(metin: str) -> str:
    return (
        str(metin).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _cubuk(oran: float, renk: str) -> str:
    # Qt zengin metin motoru yuzdelik hucre genisligini guvenilir cizmiyor: piksel kullan.
    tam = 200
    dolu = max(0, min(tam, round(oran * tam)))
    hucreler = ""
    if dolu:
        hucreler += f'<td width="{dolu}" style="background:{renk};">&nbsp;</td>'
    if tam - dolu:
        hucreler += f'<td width="{tam - dolu}" style="background:#e4e4e4;">&nbsp;</td>'
    return f'<table cellspacing="0" cellpadding="0" border="0"><tr>{hucreler}</tr></table>'


def sonuc_html(yanit: SystemOneResponse, karar_satirlari: list[str]) -> str:
    p = [f"<p style='font-family:monospace;'><b>Model:</b> {_kacir(yanit.model)}</p>"]

    if yanit.nouls:
        p.append("<h3>Noul — evet olasılığı</h3><table cellpadding='4' style='font-family:monospace;'>")
        for ad, cevap in yanit.nouls.items():
            renk = "#c0392b" if cevap.noul >= 0.7 else ("#e08b00" if cevap.noul >= 0.4 else "#2e7d32")
            p.append(
                f"<tr><td><b>{_kacir(ad)}</b></td><td>{cevap.noul:.3f}</td>"
                f"<td>{_cubuk(cevap.noul, renk)}</td></tr>"
            )
        p.append("</table>")

    if yanit.choices:
        p.append("<h3>Choice — seçim ve dağılım</h3>")
        for ad, cevap in yanit.choices.items():
            p.append(
                f"<p style='font-family:monospace;'><b>{_kacir(ad)}</b> → "
                f"<b>{_kacir(cevap.choice)}</b> (güven {cevap.confidence:.2f})</p>"
                "<table cellpadding='3' style='font-family:monospace;'>"
            )
            for etiket, olasilik in sorted(cevap.probabilities.items(), key=lambda kv: -kv[1]):
                p.append(
                    f"<tr><td>{_kacir(etiket)}</td><td>{olasilik:.2f}</td>"
                    f"<td>{_cubuk(olasilik, '#1565c0')}</td></tr>"
                )
            p.append("</table>")

    if yanit.scores:
        p.append("<h3>Score — beklenen değer ve seviyeler</h3>")
        for ad, cevap in yanit.scores.items():
            p.append(
                f"<p style='font-family:monospace;'><b>{_kacir(ad)}</b> → "
                f"<b>{cevap.score:.2f}</b> (güven {cevap.confidence:.2f})</p>"
                "<table cellpadding='3' style='font-family:monospace;'>"
            )
            for seviye, olasilik in sorted(cevap.probabilities.items()):
                p.append(
                    f"<tr><td>{seviye}</td><td>{olasilik:.2f}</td>"
                    f"<td>{_cubuk(olasilik, '#6a1b9a')}</td>"
                    f"<td>{_kacir(cevap.legend.get(seviye, ''))}</td></tr>"
                )
            p.append("</table>")

    if karar_satirlari:
        p.append("<h3>Karar (eşikler ve birleştirme kodda)</h3>")
        p.append("<div style='font-family:monospace;border:1px solid #888;padding:8px;'>")
        p.append("<br>".join(_kacir(satir) for satir in karar_satirlari))
        p.append("</div>")

    u = yanit.usage
    p.append(f"<p style='color:#666;'>Kullanım: {u.input_tokens} giriş / {u.output_tokens} çıkış token</p>")
    return "".join(p)


# ==============================================================================================
# Ana pencere
# ==============================================================================================
QShortcut = getattr(QtGui, "QShortcut", None) or QtWidgets.QShortcut  # PyQt6/PyQt5 farkı


class JevPencere(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jev — bankacılık senaryo denemeleri")
        self.resize(1280, 860)
        self.setAcceptDrops(True)

        self._isci: Isci | None = None
        self._senaryolar: list[Senaryo] = list(GOMULU_SENARYOLAR)

        self._arayuzu_kur()
        self._listeyi_doldur()
        self.liste.setCurrentRow(0)

    # --- arayüz kurulumu ----------------------------------------------------------------------
    def _arayuzu_kur(self) -> None:
        ust = QtWidgets.QWidget()
        ust_duzen = QtWidgets.QHBoxLayout(ust)
        ust_duzen.setContentsMargins(8, 6, 8, 6)

        self.anahtar_alani = QtWidgets.QLineEdit(API_KEY or os.environ.get("TYPESAFE_API_KEY", ""))
        self.anahtar_alani.setEchoMode(SIFRE_MODU)
        self.anahtar_alani.setPlaceholderText("API anahtarı (ts-...) — boşsa TYPESAFE_API_KEY")
        self.model_alani = QtWidgets.QLineEdit(MODEL)
        self.model_alani.setPlaceholderText("model (boş = varsayılan)")
        self.model_alani.setMaximumWidth(200)
        self.proxy_alani = QtWidgets.QLineEdit(PROXY)
        self.proxy_alani.setPlaceholderText("proxy (opsiyonel)")
        self.proxy_alani.setMaximumWidth(220)

        self.calistir_dugme = QtWidgets.QPushButton("Çalıştır  (Ctrl+Enter)")
        self.calistir_dugme.clicked.connect(self.calistir)
        yukle_dugme = QtWidgets.QPushButton("JSON yükle…")
        yukle_dugme.clicked.connect(self.json_yukle)
        kaydet_dugme = QtWidgets.QPushButton("JSON kaydet…")
        kaydet_dugme.clicked.connect(self.json_kaydet)

        for parca in (
            QtWidgets.QLabel("Anahtar:"), self.anahtar_alani,
            QtWidgets.QLabel("Model:"), self.model_alani,
            QtWidgets.QLabel("Proxy:"), self.proxy_alani,
            self.calistir_dugme, yukle_dugme, kaydet_dugme,
        ):
            ust_duzen.addWidget(parca)

        self.liste = QtWidgets.QListWidget()
        self.liste.setMinimumWidth(270)
        self.liste.currentRowChanged.connect(self._senaryo_secildi)

        self.state_alani = QtWidgets.QPlainTextEdit()
        self.sorular_alani = QtWidgets.QPlainTextEdit()
        for alan in (self.state_alani, self.sorular_alani):
            alan.setLineWrapMode(SARMA_YOK)
            alan.setFont(QtGui.QFont("Monospace", 10))

        self.sonuc_alani = QtWidgets.QTextBrowser()
        self.sonuc_alani.setOpenExternalLinks(False)

        sol = QtWidgets.QWidget()
        sol_duzen = QtWidgets.QVBoxLayout(sol)
        sol_duzen.setContentsMargins(0, 0, 0, 0)
        sol_duzen.addWidget(QtWidgets.QLabel("Senaryolar"))
        sol_duzen.addWidget(self.liste)
        self.aciklama_etiketi = QtWidgets.QLabel("")
        self.aciklama_etiketi.setWordWrap(True)
        self.aciklama_etiketi.setMinimumHeight(52)
        sol_duzen.addWidget(self.aciklama_etiketi)

        orta = QtWidgets.QSplitter(DIKEY)
        orta.addWidget(self._kutu("State (JSON)", self.state_alani))
        orta.addWidget(self._kutu("Questions (JSON)", self.sorular_alani))
        orta.addWidget(self._kutu("Sonuç", self.sonuc_alani))
        orta.setSizes([220, 320, 360])

        bolucu = QtWidgets.QSplitter(YATAY)
        bolucu.addWidget(sol)
        bolucu.addWidget(orta)
        bolucu.setSizes([280, 1000])

        govde = QtWidgets.QWidget()
        govde_duzen = QtWidgets.QVBoxLayout(govde)
        govde_duzen.setContentsMargins(0, 0, 0, 0)
        govde_duzen.addWidget(ust)
        govde_duzen.addWidget(bolucu, 1)
        self.setCentralWidget(govde)

        self.statusBar().showMessage(
            "Hazır. JSON talimat yüklemek için dosyayı pencereye sürükleyebilirsin."
        )
        QShortcut(QtGui.QKeySequence("Ctrl+Return"), self, activated=self.calistir)
        QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self, activated=self.calistir)

    @staticmethod
    def _kutu(baslik: str, icerik: QtWidgets.QWidget) -> QtWidgets.QWidget:
        kutu = QtWidgets.QWidget()
        duzen = QtWidgets.QVBoxLayout(kutu)
        duzen.setContentsMargins(6, 4, 6, 4)
        etiket = QtWidgets.QLabel(baslik)
        etiket.setStyleSheet("font-weight:bold;")
        duzen.addWidget(etiket)
        duzen.addWidget(icerik, 1)
        return kutu

    # --- senaryo listesi ----------------------------------------------------------------------
    def _listeyi_doldur(self) -> None:
        self.liste.clear()
        for senaryo in self._senaryolar:
            oge = QtWidgets.QListWidgetItem(senaryo.baslik)
            oge.setData(KULLANICI_ROL, senaryo.baslik)
            self.liste.addItem(oge)

    def _senaryo_secildi(self, satir: int) -> None:
        if not 0 <= satir < len(self._senaryolar):
            return
        senaryo = self._senaryolar[satir]
        self.state_alani.setPlainText(json.dumps(senaryo.state, ensure_ascii=False, indent=2))
        self.sorular_alani.setPlainText(json.dumps(senaryo.sorular, ensure_ascii=False, indent=2))
        self.aciklama_etiketi.setText(senaryo.aciklama)
        self.sonuc_alani.setHtml(
            "<p style='color:#666;'>Çalıştır'a bas (Ctrl+Enter). "
            "State ve Questions panolarındaki JSON neyse o gönderilir.</p>"
        )

    def _secili_senaryo(self) -> Senaryo | None:
        satir = self.liste.currentRow()
        return self._senaryolar[satir] if 0 <= satir < len(self._senaryolar) else None

    # --- JSON talimat yükleme -----------------------------------------------------------------
    def json_yukle(self) -> None:
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(self, "JSON talimat seç", "", "JSON (*.json);;Tüm dosyalar (*)")
        if yol:
            self.dosyadan_yukle(yol)

    def dosyadan_yukle(self, yol: str) -> None:
        try:
            with open(yol, encoding="utf-8") as dosya:
                veri = json.load(dosya)
        except (OSError, json.JSONDecodeError) as hata:
            QtWidgets.QMessageBox.warning(self, "JSON okunamadı", f"{yol}\n\n{hata}")
            return

        kaynak = os.path.basename(yol)
        yeni = talimat_coz(veri, kaynak)
        if not yeni:
            QtWidgets.QMessageBox.warning(self, "Tanınmayan JSON", "Dosyadan senaryo çıkarılamadı.")
            return

        ilk = len(self._senaryolar)
        self._senaryolar += yeni
        self._listeyi_doldur()
        self.liste.setCurrentRow(ilk)
        self.statusBar().showMessage(f"{kaynak}: {len(yeni)} senaryo yüklendi.")

    def json_kaydet(self) -> None:
        try:
            veri = {"state": json.loads(self.state_alani.toPlainText() or "{}"),
                    "questions": json.loads(self.sorular_alani.toPlainText() or "{}")}
        except json.JSONDecodeError as hata:
            QtWidgets.QMessageBox.warning(self, "JSON hatalı", str(hata))
            return
        senaryo = self._secili_senaryo()
        if senaryo:
            veri = {"baslik": senaryo.baslik, **veri}
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(self, "JSON olarak kaydet", "talimat.json", "JSON (*.json)")
        if yol:
            with open(yol, "w", encoding="utf-8") as dosya:
                json.dump(veri, dosya, ensure_ascii=False, indent=2)
            self.statusBar().showMessage(f"Kaydedildi: {yol}")

    # --- sürükle-bırak ------------------------------------------------------------------------
    def dragEnterEvent(self, olay: Any) -> None:  # noqa: N802 - Qt adlandirmasi
        if olay.mimeData().hasUrls():
            olay.acceptProposedAction()

    def dropEvent(self, olay: Any) -> None:  # noqa: N802 - Qt adlandirmasi
        for url in olay.mimeData().urls():
            yol = url.toLocalFile()
            if yol.lower().endswith(".json"):
                self.dosyadan_yukle(yol)

    # --- çalıştırma ---------------------------------------------------------------------------
    def calistir(self) -> None:
        if self._isci is not None and self._isci.isRunning():
            return
        try:
            state = json.loads(self.state_alani.toPlainText() or "{}")
            sorular = json.loads(self.sorular_alani.toPlainText() or "{}")
        except json.JSONDecodeError as hata:
            QtWidgets.QMessageBox.warning(self, "JSON hatalı", f"Panolardaki JSON okunamadı:\n\n{hata}")
            return

        if not soru_seti_mi(sorular):
            QtWidgets.QMessageBox.warning(
                self,
                "Soru seti eksik",
                'Questions panosu {"ad": {"type": "noul"|"choice"|"score", ...}} biçiminde olmalı.',
            )
            return

        self.calistir_dugme.setEnabled(False)
        self.statusBar().showMessage("İstek gönderildi…")
        self.sonuc_alani.setHtml("<p style='color:#666;'>Bekleniyor…</p>")

        self._isci = Isci(
            state,
            sorular,
            self.anahtar_alani.text().strip(),
            self.proxy_alani.text().strip(),
            self.model_alani.text().strip(),
        )
        self._isci.bitti.connect(self._yanit_geldi)
        self._isci.hata.connect(self._hata_geldi)
        self._isci.finished.connect(lambda: self.calistir_dugme.setEnabled(True))
        self._isci.start()

    def _yanit_geldi(self, yanit: SystemOneResponse) -> None:
        senaryo = self._secili_senaryo()
        satirlar: list[str] = []
        if senaryo is not None and senaryo.karar is not None:
            try:
                satirlar = senaryo.karar(yanit)
            except KeyError as eksik:
                satirlar = [
                    f"Karar mantığı çalıştırılamadı: {eksik} sorusu yanıtta yok "
                    "(soru adlarını değiştirdiysen bu normaldir)."
                ]
        self.sonuc_alani.setHtml(sonuc_html(yanit, satirlar))
        u = yanit.usage
        self.statusBar().showMessage(
            f"Tamam — model {yanit.model} | {u.input_tokens} giriş / {u.output_tokens} çıkış token"
        )

    def _hata_geldi(self, mesaj: str) -> None:
        self.sonuc_alani.setHtml(f"<p style='color:#b00;font-family:monospace;'>{_kacir(mesaj)}</p>")
        self.statusBar().showMessage(mesaj)


def main() -> int:
    uygulama = QtWidgets.QApplication(sys.argv)
    pencere = JevPencere()
    for arguman in sys.argv[1:]:  # python jev_pyqt.py talimat.json
        if arguman.lower().endswith(".json"):
            pencere.dosyadan_yukle(arguman)
    pencere.show()
    calistir = getattr(uygulama, "exec", None) or uygulama.exec_
    return calistir()


if __name__ == "__main__":
    sys.exit(main())
