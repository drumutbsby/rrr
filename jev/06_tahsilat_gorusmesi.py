"""06 — Tahsilat görüşmesi: ödeme vaadi, hassas müşteri ve görüşme kalitesi.

Senaryo:  90 gün gecikmiş bireysel kredi için çağrı merkezi aramasının dökümü.
          Tek çağrıda üç ayrı şey belirlenmeli: (1) tahsil edilebilir mi,
          (2) müşteri korunması gereken durumda mı, (3) temsilci mevzuata
          aykırı bir dil kullandı mı (TKHK/BDDK tahsilat ilkeleri).

Jev'e sorulan:  konuşmanın içeriği — vaat var mı, zorluk beyanı gerçek mi,
                temsilcinin tutumu uygun mu.
Kodda kalan:    gecikme gün sayısı, yapılandırma uygunluğu, bir sonraki temas takvimi.

Çalıştırma: python jev/06_tahsilat_gorusmesi.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

GECIKME_GUN = 92
BORC_TL = 74_300.0

STATE = {
    "dosya": {"urun": "ihtiyac_kredisi", "gecikme_gun": GECIKME_GUN, "bakiye_tl": BORC_TL, "onceki_vaat_sayisi": 2},
    "gorusme_dokumu": [
        {"taraf": "temsilci", "metin": "İyi günler, 74.300 TL gecikmiş borcunuz için arıyorum. Bugün ödeme yapabilecek misiniz?"},
        {"taraf": "musteri", "metin": "Eşim altı ay önce vefat etti, tek gelir bendim, şubatta da işten çıkarıldım. Şu an işsizlik maaşı alıyorum, 14 bin lira."},
        {"taraf": "temsilci", "metin": "Anlıyorum ama bu borç sizin sorumluluğunuzda. Ödemezseniz icra takibi başlar, evinize haciz gelir."},
        {"taraf": "musteri", "metin": "Biliyorum, kaçmıyorum. Ayda 3 bin lira ödeyebilirim, daha fazlasına gücüm yetmez. Doktor raporum da var, depresyon tedavisi görüyorum."},
        {"taraf": "temsilci", "metin": "3 bin lira olmaz, en az 10 bin lira ödemeniz gerekiyor, yoksa dosyayı avukata devrederim. Akrabalarınızdan borç alın."},
        {"taraf": "musteri", "metin": "Bu ay 3 bin lirayı 28'inde yatırırım, söz veriyorum. Gerisi için yapılandırma istiyorum."},
    ],
}

SORULAR = {
    "odeme_vaadi": Noul(
        instructions="The customer commits to a specific payment amount on a specific date.",
        criteria={
            "true": "A concrete amount and a date are stated by the customer.",
            "false": "The customer makes no concrete commitment, or only says they will 'try'.",
        },
    ),
    "mali_zorluk_beyani": Noul(
        instructions="The customer states a genuine change in circumstances that reduced their ability to pay.",
        criteria={
            "true": "Job loss, illness, bereavement, disability or a similar event is described.",
            "false": "No such event is described; the customer simply refuses or avoids payment.",
        },
    ),
    "hassas_musteri": Noul(
        instructions=(
            "The customer shows signs of vulnerability that require special care: bereavement, "
            "serious illness, mental health treatment, disability or sole reliance on state benefits."
        ),
    ),
    "odeme_niyeti_yok": Noul(
        instructions="The customer shows no intention to pay and avoids engaging with the debt.",
    ),
    "uygunsuz_tahsilat_dili": Noul(
        instructions=(
            "The collections agent used pressure, threats, or improper instructions that a regulator "
            "would treat as unfair debt collection practice."
        ),
        criteria={
            "true": "Threats beyond the bank's actual legal rights, shaming, or telling the customer to borrow from family or third parties.",
            "false": "The agent stayed factual and respectful about consequences.",
        },
    ),
    "sonraki_adim": Choice(
        instructions="What should the bank do next with this file?",
        criteria={
            "yapilandirma_teklifi": "Offer a restructuring or payment plan matched to the customer's capacity.",
            "odemesiz_donem": "Grant a temporary payment holiday because of hardship.",
            "vaadi_takip": "Record the promise to pay and follow up on the promised date.",
            "hukuki_takip": "Move the file to legal enforcement.",
            "sosyal_destek_yonlendirme": "Pause collection and refer to the bank's vulnerable-customer process.",
        },
    ),
    "tahsil_edilebilirlik": Score(
        instructions="How likely is this debt to be recovered through voluntary payment over the next 12 months?",
        criteria=[
            "Unlikely: no capacity and no intent.",
            "Partial: some capacity, recovery only with a long, reduced plan.",
            "Likely: capacity and intent are both present.",
        ],
    ),
}


def main() -> None:
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

    n, c, s = yanit.nouls, yanit.choices, yanit.scores

    # Aylık ödeme gücü beyanı metinden değil, dosyadan alınmalı; burada sadece oran kontrolü.
    onerilen_taksit = 3_000.0
    kapanis_ay = BORC_TL / onerilen_taksit

    satirlar = [
        f"Gecikme: {GECIKME_GUN} gun | Bakiye: {BORC_TL:,.0f} TL | "
        f"Beyan edilen taksitle kapanis: ~{kapanis_ay:.0f} ay",
        f"Onerilen adim: {c['sonraki_adim'].choice} (guven {c['sonraki_adim'].confidence:.2f}) | "
        f"Tahsil edilebilirlik: {s['tahsil_edilebilirlik'].score:.2f}",
    ]

    # 1) Uyum ihlali her şeyin önüne geçer.
    if n["uygunsuz_tahsilat_dili"].noul > 0.6:
        satirlar += [
            "UYARI: tahsilat dili uygunsuz. Cagri kaydi uyum birimine gonderilsin, temsilciye geri bildirim.",
            "Aksiyon: musteri farkli bir temsilci tarafindan yeniden aransin; bu gorusmedeki vaat baski altinda sayilsin.",
        ]

    # 2) Hassas müşteri koruması ikinci öncelik.
    if n["hassas_musteri"].noul > 0.7 and n["mali_zorluk_beyani"].noul > 0.6:
        satirlar += [
            "Karar: HASSAS MUSTERI protokolu. Hukuki takip 90 gun durdurulsun.",
            "Aksiyon: saglik raporu + issizlik odenegi belgesi istensin, odemesiz donem + vade uzatimi teklif edilsin.",
        ]
    elif n["odeme_niyeti_yok"].noul > 0.7 and s["tahsil_edilebilirlik"].score < 0.7:
        satirlar.append("Karar: hukuki takip hazirligi. Dosya avukata, teminat ve mal varligi arastirmasi baslasin.")
    elif s["tahsil_edilebilirlik"].score >= 1.4:
        satirlar.append("Karar: yapilandirma teklifi. Vade uzatimi ile taksit odeme gucune cekilsin.")
    else:
        satirlar.append("Karar: kismi tahsilat plani. Dusuk taksitli 36 ay + donemsel gozden gecirme.")

    # 3) Vaat varsa her hâlükârda takvime girer.
    if n["odeme_vaadi"].noul > 0.7:
        satirlar.append("Aksiyon: odeme vaadi kaydedilsin (28'i), vaat gunu +1 hatirlatma araması planlansin.")
    if STATE["dosya"]["onceki_vaat_sayisi"] >= 2 and n["odeme_vaadi"].noul > 0.7:
        satirlar.append("Not: ucuncu vaat — tek basina vaat takibi yeterli degil, yazili plan sart.")

    karar(satirlar)


if __name__ == "__main__":
    calistir("Tahsilat gorusmesi degerlendirmesi", main)
