"""07 — Dijital bankacılık hesap ele geçirme (SIM swap / ATO) triyajı.

Senaryo:  Müşteri çağrı merkezini arıyor: mobil uygulamaya giremiyor, telefonu
          çekmiyor. Aynı anda oturum ve cihaz telemetrisi de elde. Soru: bu bir
          teknik sorun mu, yoksa süren bir hesap ele geçirme mi?

Jev'e sorulan:  müşterinin anlattığı belirtilerin ele geçirme kalıbına uyup uymadığı
                ve arayanın gerçekten müşteri olup olmadığına dair şüphe.
Kodda kalan:    bloke kararı, kanal kapatma, yeniden kimliklendirme akışı.

Çalıştırma: python jev/07_sim_swap_hesap_ele_gecirme.py
"""

from ortak import calistir, karar, sor, yazdir
from typesafe_sdk import Choice, Noul, Score

STATE = {
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

SORULAR = {
    "sim_swap_belirtisi": Noul(
        instructions=(
            "The caller describes losing mobile network service in a way consistent with their SIM "
            "being ported or re-issued without their request."
        ),
    ),
    "ele_gecirme_suruyor": Noul(
        instructions=(
            "The recorded account events indicate an attacker is currently in control of the account "
            "and preparing to move money."
        ),
        criteria={
            "true": "Credential, contact-detail, limit or payee changes cluster together in a short window.",
            "false": "The events look like ordinary self-service activity by the customer.",
        },
    ),
    "arayan_supheli": Noul(
        instructions="There is reason to doubt that the caller is the genuine customer.",
        criteria={
            "true": "The caller's account is inconsistent, evasive, or fits a social-engineering attempt against the call centre.",
            "false": "The caller's account is coherent and matches the recorded events.",
        },
    ),
    "teknik_ariza": Noul(
        instructions="The symptoms are explained by an ordinary technical fault rather than an attack.",
    ),
    "olay_tipi": Choice(
        instructions="What is happening on this account?",
        criteria={
            "sim_swap_ato": "SIM swap used to take over the account.",
            "kimlik_avi_ato": "Credentials harvested by phishing and now used by an attacker.",
            "zararli_yazilim": "Device malware or a remote-access tool driving the session.",
            "yetkili_kisi": "A family member or acquaintance with legitimate access made the changes.",
            "teknik_sorun": "No attack: app, SIM or network fault.",
        },
    ),
    "mudahale_aciliyeti": Score(
        instructions="How fast must the bank act?",
        criteria=[
            "Routine: can be handled in the normal support queue.",
            "Same day: act within hours to prevent loss.",
            "Immediate: money is at imminent risk; act within minutes.",
        ],
    ),
}


def main() -> None:
    yanit = sor(STATE, SORULAR)
    yazdir(yanit)

    n, c, s = yanit.nouls, yanit.choices, yanit.scores
    saldiri = c["olay_tipi"].choice in {"sim_swap_ato", "kimlik_avi_ato", "zararli_yazilim"}
    acil = s["mudahale_aciliyeti"].score >= 1.5

    satirlar = [f"Olay tipi: {c['olay_tipi'].choice} (guven {c['olay_tipi'].confidence:.2f}) | Aciliyet: {s['mudahale_aciliyeti'].score:.2f}"]

    if n["ele_gecirme_suruyor"].noul > 0.7 and acil:
        satirlar += [
            "Karar: ACIL KISIT. Tum dijital kanallar kapatilsin, giden odemeler durdurulsun, aktif oturumlar sonlandirilsin.",
            "Aksiyon: son 1 saatte tanimlanan IBAN ve limit artisi geri alinsin.",
            "Aksiyon: SIM degisikligi sonrasi 72 saat OTP ile islem yapilmasin (numara bazli kisit).",
        ]
    elif saldiri:
        satirlar.append("Karar: hesabi izlemeye al, yuksek tutarli islemler icin ikinci kanal teyidi zorunlu olsun.")
    elif n["teknik_ariza"].noul > 0.7:
        satirlar.append("Karar: teknik destek kuyrugu. Kisit uygulanmasin, cihaz kaydi yenilensin.")
    else:
        satirlar.append("Karar: belirsiz. Fraud ekibi dosyayi incelesin, gecici olarak transfer limiti dusurulsun.")

    # Arayanın kimliği ayrı bir risk: ele geçirmeyi bildiren kişi saldırganın kendisi olabilir.
    if n["arayan_supheli"].noul > 0.5:
        satirlar.append(
            "Not: arayanin kimligi supheli. Telefonda islem yapilmasin; sube + kimlik ibrazi ile "
            "yeniden kimliklendirme (re-onboarding) istensin."
        )
    else:
        satirlar.append("Not: arayan beyani telemetri ile tutarli. Geri arama kayitli sabit numaradan yapilsin.")

    if n["sim_swap_belirtisi"].noul > 0.7:
        satirlar.append("Aksiyon: operatorden hat degisiklik tarihi yazili istensin — sonraki itiraz/dava dosyasinda gerekiyor.")

    karar(satirlar)


if __name__ == "__main__":
    calistir("SIM swap / hesap ele gecirme triyaji", main)
