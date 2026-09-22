"""03 — MASAK şüpheli işlem taraması (toplu / batch kullanım).

Senaryo:  Gece çalışan kural motoru, gün içinde bayrak alan hesapları uyum (compliance)
          analistinin önüne getiriyor. Analist başına 200+ dosya düşüyor; amaç,
          şüpheli işlem bildirimi (ŞİB) adayı olanları öne almak.

Jev'e sorulan:  hareket deseninin bilinen aklama tipolojilerine uyup uymadığı
                (parçalama/smurfing, mule hesap, kripto çıkışı, ticari görünümlü akış).
Kodda kalan:    ŞİB eşiği, analist kuyruğu sıralaması, 10 gün içinde bildirim takvimi.

Not:  Tek istemci açılıp birden çok kayıt için system_one çağrılıyor — bağlantı
      yeniden kullanılıyor, senaryo başına client kurulmuyor.

Çalıştırma: python jev/03_masak_supheli_islem.py
"""

from ortak import calistir, istemci, karar
from typesafe_sdk import Choice, Noul, Score

KAYITLAR = [
    {
        "musteri_no": "4471902",
        "profil": {"meslek": "ogrenci", "yas": 21, "beyan_gelir_tl": 0, "hesap_yasi_gun": 38},
        "hareketler": [
            "11 farkli gercek kisiden 3 gun icinde toplam 412.000 TL gelen havale",
            "Her gelen tutar 9.000-9.800 TL araliginda",
            "Gelen tutarlarin %94'u ayni gun icinde 3 farkli IBAN'a cikti",
            "Kalan bakiye: 2.140 TL",
        ],
    },
    {
        "musteri_no": "1180553",
        "profil": {"meslek": "insaat_muteahhidi", "yas": 47, "beyan_gelir_tl": 320_000, "hesap_yasi_gun": 2_900},
        "hareketler": [
            "Tek seferde 2.400.000 TL gelen havale — gonderen: ticari musteri, aciklama 'hakedis'",
            "Ertesi gun 1.900.000 TL tedarikcilere odendi (4 fatura referansli)",
            "Ayni hafta 180.000 TL nakit cekim — sahsi harcama beyani mevcut",
        ],
    },
    {
        "musteri_no": "9032118",
        "profil": {"meslek": "emekli", "yas": 71, "beyan_gelir_tl": 22_000, "hesap_yasi_gun": 5_100},
        "hareketler": [
            "Son 10 gunde 6 farkli ATM'den toplam 148.000 TL nakit yatirma",
            "Yatirmalarin ardindan yurtdisi kripto borsasina 3 transfer: 145.000 TL",
            "Musteri daha once hic kripto islemi yapmamis",
            "Hesaba yeni eklenen mobil cihaz: 9 gun once",
        ],
    },
]

SORULAR = {
    "parcalama": Noul(
        instructions=(
            "The account activity looks like structuring: amounts deliberately kept below a reporting "
            "threshold, or one large sum split across many smaller movements."
        ),
    ),
    "gecis_hesabi": Noul(
        instructions=(
            "The account behaves as a pass-through: money arrives and leaves almost immediately, "
            "leaving little balance behind."
        ),
        criteria={
            "true": "Incoming funds are forwarded out within a very short time, with almost nothing retained.",
            "false": "Funds stay in the account and are used in a way consistent with normal personal or business use.",
        },
    ),
    "profil_uyumsuz": Noul(
        instructions=(
            "The volume or nature of the activity is inconsistent with the customer's stated occupation, "
            "age and declared income."
        ),
    ),
    "ekonomik_gerekce_var": Noul(
        instructions="The activity has a visible, documented business or economic rationale.",
        criteria={
            "true": "Invoices, contracts, payroll, progress payments or similar explain the flow.",
            "false": "No economic explanation is visible in the records.",
        },
    ),
    "tipoloji": Choice(
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
    "sib_gerekcesi": Score(
        instructions="How strong is the case for filing a suspicious transaction report?",
        criteria=[
            "Weak: activity is explainable; monitor only.",
            "Moderate: unusual pattern that needs an analyst to request documents first.",
            "Strong: pattern matches a known typology with no plausible economic explanation.",
        ],
    ),
}


def main() -> None:
    kuyruk = []

    with istemci() as client:
        for kayit in KAYITLAR:
            yanit = client.system_one(state=kayit, questions=SORULAR)
            n, c, s = yanit.nouls, yanit.choices, yanit.scores

            bayraklar = [ad for ad, cevap in n.items() if ad != "ekonomik_gerekce_var" and cevap.noul > 0.7]
            if n["ekonomik_gerekce_var"].noul < 0.3:
                bayraklar.append("ekonomik_gerekce_yok")

            kuyruk.append(
                {
                    "musteri_no": kayit["musteri_no"],
                    "tipoloji": c["tipoloji"].choice,
                    "tipoloji_guven": c["tipoloji"].confidence,
                    "sib": s["sib_gerekcesi"].score,
                    "sib_guven": s["sib_gerekcesi"].confidence,
                    "bayraklar": bayraklar,
                }
            )

            print(
                f"{kayit['musteri_no']}  tipoloji={c['tipoloji'].choice:<22} "
                f"sib={s['sib_gerekcesi'].score:.2f}  bayrak={','.join(bayraklar) or '-'}"
            )

    # Sıralama ve eşikler kodda: analistin ekranı skora göre diziliyor.
    kuyruk.sort(key=lambda k: -k["sib"])

    satirlar = ["Analist kuyrugu (yuksek skordan dusuge):"]
    for kayit in kuyruk:
        if kayit["sib"] >= 1.6 and kayit["tipoloji"] != "olagan":
            aksiyon = "SIB adayi — 10 gun icinde MASAK bildirimi degerlendir, hesabi kisitla"
        elif kayit["sib"] >= 1.0 or kayit["tipoloji_guven"] < 0.6:
            aksiyon = "Belge talebi — musteriden kaynak beyani iste, 5 is gunu takip"
        else:
            aksiyon = "Izlemede birak — 30 gun sonra tekrar tara"
        satirlar.append(f"  {kayit['musteri_no']}  skor {kayit['sib']:.2f}  -> {aksiyon}")

    karar(satirlar)


if __name__ == "__main__":
    calistir("MASAK supheli islem taramasi (toplu)", main)
