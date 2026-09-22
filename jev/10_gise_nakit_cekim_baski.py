"""10 — Gişede yüksek tutarlı nakit çekim: baskı altındaki müşteri.

Senaryo:  Şube gişesinde 75 yaşındaki müşteri, vadeli hesabını bozdurup 350.000 TL
          nakit çekmek istiyor. Yanında bir kişi var. Gişe personeli görüşme notunu
          sisteme giriyor; karar, müşteriyi incitmeden ama zararı önleyerek verilmeli.

Jev'e sorulan:  anlatılan durumun baskı/istismar kalıbına uyup uymadığı, verilen
                gerekçenin tutarlılığı, müşterinin kendi iradesiyle hareket edip etmediği.
Kodda kalan:    nakit tutar eşiği, ikinci imza, kolluk bildirimi, işlemi geciktirme yetkisi.

Çalıştırma: python jev/10_gise_nakit_cekim_baski.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

TUTAR = 350_000.0

STATE = {
    "musteri": {"yas": 75, "sube_musterisi_yil": 22, "son_1_yil_nakit_cekim_ortalama_tl": 12_000},
    "islem": {"tip": "nakit_cekim", "tutar_tl": TUTAR, "vadeli_hesap_bozuldu": True, "faiz_kaybi_tl": 41_000},
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

SORULAR = {
    "baski_altinda": Noul(
        instructions=(
            "The customer appears to be acting under pressure or direction from the person accompanying them."
        ),
        criteria={
            "true": "The companion answers for the customer, corrects them, or the customer looks to them before responding.",
            "false": "The customer speaks and decides for themselves.",
        },
    ),
    "gerekce_tutarsiz": Noul(
        instructions="The stated reason for the withdrawal does not hold up under simple questioning.",
    ),
    "banka_gorevlisi_taklidi": Noul(
        instructions=(
            "The customer repeats the claim that the bank or an official told them to move money to a "
            "'safe account', a classic impersonation scam."
        ),
    ),
    "yakin_istismari": Noul(
        instructions="The situation fits financial abuse of an older person by a relative, carer or acquaintance.",
    ),
    "kendi_iradesi": Noul(
        instructions="The customer understands the transaction and its cost and genuinely wants it.",
        criteria={
            "true": "The customer explains the purpose consistently and accepts the cost knowingly.",
            "false": "The customer is confused about the purpose or unaware of what they are giving up.",
        },
    ),
    "durum": Choice(
        instructions="What best describes this counter request?",
        criteria={
            "guvenli_hesap_dolandiriciligi": "Impersonation scam telling the customer to move money for safety.",
            "yakin_istismari": "Financial abuse by a family member, carer or acquaintance.",
            "ucuncu_kisi_yonlendirmesi": "The customer is being directed by someone they met recently.",
            "mesru_ihtiyac": "A genuine personal need for cash.",
            "belirsiz": "There is not enough in the note to tell.",
        },
    ),
    "mudahale_gerekliligi": Score(
        instructions="How strongly should the branch intervene before releasing the cash?",
        criteria=[
            "None: complete the transaction normally.",
            "Speak privately: separate the customer from the companion and ask again.",
            "Withhold: delay the transaction and escalate before any cash leaves.",
        ],
    ),
}


def main() -> None:
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

    n, c, s = yanit.nouls, yanit.choices, yanit.scores
    korunmasiz = STATE["musteri"]["yas"] >= 70
    olagan_disi_tutar = TUTAR >= 10 * STATE["musteri"]["son_1_yil_nakit_cekim_ortalama_tl"]
    mudahale = s["mudahale_gerekliligi"].score

    satirlar = [
        f"Tutar: {TUTAR:,.0f} TL (ortalamanin {TUTAR / STATE['musteri']['son_1_yil_nakit_cekim_ortalama_tl']:.0f} kati) | "
        f"Faiz kaybi: 41.000 TL | Durum: {c['durum'].choice} (guven {c['durum'].confidence:.2f})",
    ]

    if n["banka_gorevlisi_taklidi"].noul > 0.6:
        satirlar += [
            "Karar: ISLEMI TAMAMLAMA. 'Guvenli hesap' anlatisi banka gorevlisi taklidi dolandiriciligidir.",
            "Aksiyon: musteri ayri bir odaya alinsin, refakatci disarida kalsin, kolluk (155) bilgilendirilsin.",
        ]
    elif mudahale >= 1.5 and (n["baski_altinda"].noul > 0.6 or n["gerekce_tutarsiz"].noul > 0.6):
        satirlar += [
            "Karar: ISLEMI BEKLET. Nakit teslim edilmesin, sube muduru ikinci gorusmeyi yapsin.",
            "Aksiyon: musteri yalniz gorusulsun; kayitli yakin/temsilci aranarak teyit alinsin.",
        ]
    elif mudahale >= 0.8:
        satirlar.append("Karar: once ozel gorusme. Musteri refakatciden ayri sorgulansin, sonra karar verilsin.")
    elif n["kendi_iradesi"].noul > 0.7 and c["durum"].choice == "mesru_ihtiyac":
        satirlar.append("Karar: islem yapilsin. Faiz kaybi yazili teyit alinarak nakit teslim edilsin.")
    else:
        satirlar.append("Karar: belirsiz. Sube muduru onayina sunulsun, tutar bugun icin dusurulmesi onerilsin.")

    if korunmasiz and (n["yakin_istismari"].noul > 0.5 or n["baski_altinda"].noul > 0.5):
        satirlar.append("Not: korunmasiz musteri istismari suphesi. Olay tutanaga baglansin, kamera kaydi saklansin.")
    if olagan_disi_tutar:
        satirlar.append("Not: olagandisi nakit hareketi — MASAK degerlendirmesi icin uyum birimine bilgi notu.")
    if n["kendi_iradesi"].noul < 0.4:
        satirlar.append("Not: musteri islemin sonucunu kavramamis olabilir; aydinlatma tekrarlansin, aceleye getirilmesin.")

    karar(satirlar)


if __name__ == "__main__":
    calistir("Gisede yuksek tutarli nakit cekim", main)
