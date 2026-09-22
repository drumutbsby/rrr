"""10 — Gişede yüksek tutarlı nakit çekim: baskı altındaki müşteri.

Senaryo:  Şube gişesinde 75 yaşındaki müşteri, vadeli hesabını bozdurup 350.000 TL
          nakit çekmek istiyor. Yanında bir kişi var. Gişe personeli görüşme notunu
          sisteme giriyor; karar, müşteriyi incitmeden ama zararı önleyerek verilmeli.

Jev'e sorulan:  anlatılan durumun baskı/istismar kalıbına uyup uymadığı, verilen
                gerekçenin tutarlılığı, müşterinin kendi iradesiyle hareket edip etmediği.
Kodda kalan:    nakit tutar eşiği, ikinci imza, kolluk bildirimi, işlemi geciktirme yetkisi.

Kurulum:  pip install typesafe-sdk
          (Colab: ilk hücrede  !pip install -q typesafe-sdk  — pydantic sürüm uyarısı
           çıkarsa "Çalışma zamanını yeniden başlat" deyip hücreyi tekrar çalıştır.)
Anahtar:  Aşağıdaki API_KEY satırına tırnakların arasına yapıştır.
          (Boş bırakırsan önce Colab Secrets, sonra TYPESAFE_API_KEY ortam
           değişkeni denenir.)
Proxy:    Gerekiyorsa PROXY satırına yaz, örn. "http://kullanici:sifre@proxy:8080"

Çalıştırma: tek parça — dosyanın tamamını bir Colab hücresine yapıştırıp çalıştır,
            ya da yerelde:  python 10_gise_nakit_cekim_baski.py
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
    print("### Gisede yuksek tutarli nakit cekim\n")

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
