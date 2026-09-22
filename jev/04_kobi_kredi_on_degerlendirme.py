"""04 — KOBİ kredi başvurusu ön değerlendirme (dosya triyajı).

Senaryo:  Şube, 3.000.000 TL işletme kredisi başvurusu açıyor. Kredi tahsis birimine
          gitmeden önce dosyanın eksiksiz mi, beyanların tutarlı mı olduğu ve
          hangi kuyruğa düşeceği belirleniyor.

Jev'e sorulan:  serbest metin (şube görüşme notu + faaliyet açıklaması) ile sayısal
                tablonun birbirini tutup tutmadığı, kredi amacının ne olduğu.
Kodda kalan:    rasyolar (borç/özkaynak, DSCR), limit eşikleri, yetki kademesi.

Çalıştırma: python jev/04_kobi_kredi_on_degerlendirme.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

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
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

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
    karar(satirlar)


if __name__ == "__main__":
    calistir("KOBI kredi basvurusu on degerlendirme", main)
