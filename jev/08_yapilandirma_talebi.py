"""08 — Bireysel kredi yapılandırma talebi (serbest metin e-posta).

Senaryo:  Müşteri, henüz gecikmeye düşmeden yapılandırma istiyor. Gelen kutusuna
          günde yüzlerce böyle e-posta düşüyor; hangi ürünün teklif edileceği ve
          hangilerinin belge istemeden karara bağlanabileceği ayrıştırılmalı.

Jev'e sorulan:  e-postanın gerçekten yapılandırma talebi mi olduğu, zorluğun
                geçici/kalıcı olduğu, hangi çözümün istendiği, şikâyet tonu.
Kodda kalan:    ürün uygunluk matrisi, kalan vade, taksit/gelir oranı.

Çalıştırma: python jev/08_yapilandirma_talebi.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

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
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

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

    karar(satirlar)


if __name__ == "__main__":
    calistir("Bireysel kredi yapilandirma talebi", main)
