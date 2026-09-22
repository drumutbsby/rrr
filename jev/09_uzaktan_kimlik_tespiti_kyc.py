"""09 — Uzaktan müşteri edinimi: video kimlik tespiti + KYC/PEP kontrolü.

Senaryo:  Mobil uygulamadan hesap açılışı. Video görüşme tamamlandı; operatör
          tutanağı, cihaz/oturum verisi ve müşterinin beyanı bir arada.
          BDDK uzaktan kimlik tespiti tebliği gereği şüpheli hâllerde görüşme
          sonlandırılıp süreç yeniden başlatılmalı.

Jev'e sorulan:  tutanaktaki gözlemlerin sahtecilik/yönlendirme belirtisi olup
                olmadığı, hesabın başkası adına açılıp açılmadığı, beyan-profil tutarlılığı.
Kodda kalan:    red/onay eşiği, risk sınıfı, başlangıç limitleri, PEP onay kademesi.

Çalıştırma: python jev/09_uzaktan_kimlik_tespiti_kyc.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

STATE = {
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

SORULAR = {
    "baskasi_adina_hesap": Noul(
        instructions=(
            "The account appears to be opened for someone else's use rather than the applicant's own."
        ),
        criteria={
            "true": "The applicant is prompted by a third party, does not know their own declared details, or the card/access is destined for another person.",
            "false": "The applicant clearly opens and will use the account themselves.",
        },
    ),
    "yonlendirilme_belirtisi": Noul(
        instructions="During the video call the applicant appears to be coached or read answers supplied by someone else.",
    ),
    "belge_supheli": Noul(
        instructions="The identity or address documents show signs of tampering or do not belong to the applicant.",
    ),
    "beyan_profil_uyumsuz": Noul(
        instructions=(
            "The declared income and transaction volume are inconsistent with the applicant's age, "
            "occupation and stated circumstances."
        ),
    ),
    "pep_baglantisi": Noul(
        instructions=(
            "The applicant is, or is a close associate or family member of, a politically exposed person."
        ),
        criteria={
            "true": "The applicant or a close relative holds or held a prominent public function.",
            "false": "No connection to a public function is described.",
        },
    ),
    "red_gerekcesi": Choice(
        instructions="If this application cannot be completed as-is, what is the main reason?",
        criteria={
            "kimlik_supheli": "Doubt about who the applicant is.",
            "para_katiri_supheli": "The account is likely to be used as a mule account.",
            "belge_eksik": "Documents are missing or invalid but the applicant seems genuine.",
            "yuksek_risk_profil": "Genuine applicant, but the risk profile needs enhanced due diligence.",
            "engel_yok": "Nothing blocks completion.",
        },
    ),
    "musteri_riski": Score(
        instructions="What customer risk rating does this application deserve?",
        criteria=[
            "Low: simplified due diligence is sufficient.",
            "Standard: normal due diligence.",
            "High: enhanced due diligence, senior approval and ongoing monitoring required.",
        ],
    ),
}


def main() -> None:
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

    n, c, s = yanit.nouls, yanit.choices, yanit.scores
    risk = s["musteri_riski"].score

    satirlar = [
        f"Red gerekcesi: {c['red_gerekcesi'].choice} (guven {c['red_gerekcesi'].confidence:.2f}) | "
        f"Musteri riski: {risk:.2f}"
    ]

    # Tebliğ gereği: şüphe hâlinde görüşme sonlandırılır, süreç baştan başlar.
    if n["belge_supheli"].noul > 0.6 or n["baskasi_adina_hesap"].noul > 0.7:
        satirlar += [
            "Karar: BASVURU REDDI. Uzaktan kimlik tespiti tamamlanmasin, gorusme kaydi saklansin.",
            "Aksiyon: cihaz/IP kara listeye, ayni cihazdan yapilan onceki 2 basvuru geriye donuk incelensin.",
            "Aksiyon: para katiri suphesi uyum birimine bildirilsin.",
        ]
    elif n["yonlendirilme_belirtisi"].noul > 0.6:
        satirlar.append("Karar: gorusme sonlandirilsin, musteri sube kanaliyla yuz yuze kimlik tespitine yonlendirilsin.")
    elif risk >= 1.6 or n["beyan_profil_uyumsuz"].noul > 0.7:
        satirlar += [
            "Karar: SIKILASTIRILMIS TEDBIR ile ac. Baslangic limitleri dusuk (gunluk 25.000 TL), kart teslimi adrese kisitli.",
            "Aksiyon: gelir ve fon kaynagi belgesi 30 gun icinde istensin, alinmazsa hesap kisitlansin.",
        ]
    elif c["red_gerekcesi"].choice == "belge_eksik":
        satirlar.append("Karar: eksik belge tamamlansin (adres belgesi basvuru sahibi adina olmali), sonra tekrar degerlendir.")
    else:
        satirlar.append("Karar: standart musteri edinimi. Normal limitler.")

    if n["pep_baglantisi"].noul > 0.5:
        satirlar.append(
            "Not: PEP/PEP yakini beyani var. Hesap acilisi ust duzey yonetici onayina baglansin, "
            "fon kaynagi yazili alinsin, surekli izleme acilsin."
        )
    if STATE["cihaz"]["ekran_paylasimi_tespiti"] == "aktif":
        satirlar.append("Not: gorusme sirasinda ekran paylasimi aktifti — tek basina red sebebi, teknik kontrol kaydi tutulsun.")

    karar(satirlar)


if __name__ == "__main__":
    calistir("Uzaktan kimlik tespiti / KYC degerlendirmesi", main)
