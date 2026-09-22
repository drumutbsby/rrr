"""09 — Uzaktan müşteri edinimi: video kimlik tespiti + KYC/PEP kontrolü.

Senaryo:  Mobil uygulamadan hesap açılışı. Video görüşme tamamlandı; operatör
          tutanağı, cihaz/oturum verisi ve müşterinin beyanı bir arada.
          BDDK uzaktan kimlik tespiti tebliği gereği şüpheli hâllerde görüşme
          sonlandırılıp süreç yeniden başlatılmalı.

Jev'e sorulan:  tutanaktaki gözlemlerin sahtecilik/yönlendirme belirtisi olup
                olmadığı, hesabın başkası adına açılıp açılmadığı, beyan-profil tutarlılığı.
Kodda kalan:    red/onay eşiği, risk sınıfı, başlangıç limitleri, PEP onay kademesi.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 09_uzaktan_kimlik_tespiti_kyc.py
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
    print("### Uzaktan kimlik tespiti / KYC degerlendirmesi\n")

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
