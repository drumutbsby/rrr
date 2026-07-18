# -*- coding: utf-8 -*-
"""
Moralite — İstihbarat Modülü
Yerel Ollama modelleriyle sohbet eden Flask sunucusu.

Çalıştırma:  python app.py
Arayüz:      http://localhost:8770
Gereksinim:  Ollama'nın çalışıyor olması (http://localhost:11434)
"""
import json
from datetime import date, datetime

import requests
from flask import Flask, Response, jsonify, request, send_from_directory

from moduller import belgeler, bilgi_tabani, kap_analiz, rapor_motoru, web_istihbarat

OLLAMA_URL = "http://localhost:11434"
PORT = 8770
VARSAYILAN_MODEL = "qwen3.5:9b"
# Sorgu üretimi de ana modelde: tek model bellekte kalır, 4b/9b arası
# yükleme-boşaltma turlarından kaçınılır (16 GB RAM'de daha akıcı).
HIZLI_MODEL = VARSAYILAN_MODEL
# Bu boyuta kadar belge metni doğrudan bağlama gömülür; üzeri vektör indekslenir
BELGE_INLINE_SINIRI = 40000
# Rapor Motoru'nun kullandığı son istihbarat çalışması (tek kullanıcılı araç)
SON_ISTIHBARAT = {"veri": None}

_yetenek_onbellek = {}


def model_yetenekleri(model):
    """Modelin yeteneklerini (vision/tools/thinking) /api/show'dan alır, önbellekler."""
    if model not in _yetenek_onbellek:
        try:
            r = requests.post(f"{OLLAMA_URL}/api/show", json={"model": model}, timeout=10)
            r.raise_for_status()
            _yetenek_onbellek[model] = set(r.json().get("capabilities", []))
        except requests.RequestException:
            return set()  # önbellekleme yapma, sonra tekrar dene
    return _yetenek_onbellek[model]

app = Flask(__name__, static_folder="static")


@app.before_request
def yalnizca_yerel():
    # DNS rebinding koruması: Host başlığı yerel değilse reddet
    if request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        return jsonify({"hata": "yalnızca yerel erişime izin verilir"}), 403


@app.get("/")
def anasayfa():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/durum")
def durum():
    """Ollama erişilebilir mi, hangi model bellekte yüklü?"""
    try:
        surum = requests.get(f"{OLLAMA_URL}/api/version", timeout=3).json()
        yuklu = requests.get(f"{OLLAMA_URL}/api/ps", timeout=3).json().get("models", [])
        return jsonify({
            "cevrimici": True,
            "surum": surum.get("version", "?"),
            "yuklu_modeller": [m["name"] for m in yuklu],
        })
    except requests.RequestException:
        return jsonify({"cevrimici": False, "surum": None, "yuklu_modeller": []})


@app.get("/api/modeller")
def modeller():
    """Diskteki modelleri listele (arayüzdeki model seçici için)."""
    try:
        veri = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except requests.RequestException:
        return jsonify({"hata": "Ollama'ya ulaşılamıyor"}), 502
    liste = [
        {
            "ad": m["name"],
            "boyut_gb": round(m.get("size", 0) / 1e9, 1),
            "gorur": "vision" in model_yetenekleri(m["name"]),
        }
        for m in veri.get("models", [])
    ]
    liste.sort(key=lambda m: m["ad"])
    return jsonify({"modeller": liste, "varsayilan": VARSAYILAN_MODEL})


@app.post("/api/belge")
def belge_yukle():
    """Multipart belge yükleme: metin çıkarılır; büyükse vektör indekslenir."""
    dosya = request.files.get("dosya")
    if not dosya or not dosya.filename:
        return jsonify({"hata": "dosya gelmedi"}), 400
    try:
        meta = belgeler.kaydet(dosya.filename, dosya.read())
    except ValueError as e:
        return jsonify({"hata": str(e)}), 400
    meta["indeksli"] = False
    if meta["karakter"] > BELGE_INLINE_SINIRI:
        try:
            belge = belgeler.getir(meta["id"])
            meta["parca"] = bilgi_tabani.indeksle(OLLAMA_URL, belge)
            meta["indeksli"] = True
        except Exception as e:
            return jsonify({"hata": f"indeksleme hatası: {e}"}), 502
    return jsonify(meta)


def _belge_baglami(belge_idler: list, soru: str) -> str | None:
    """Ekli belgelerden bağlam bloğu üretir: küçükler tam metin, büyükler
    soruya en yakın parçalar (vektör araması)."""
    bloklar, buyukler = [], []
    for bid in belge_idler:
        b = belgeler.getir(bid)
        if not b:
            continue
        if b["karakter"] <= BELGE_INLINE_SINIRI:
            bloklar.append(f"[BELGE: {b['ad']} — tam metin]\n{b['metin']}")
        else:
            buyukler.append(b)
    if buyukler and soru:
        try:
            parcalar = bilgi_tabani.ara(
                OLLAMA_URL, soru, [b["id"] for b in buyukler], k=6)
        except Exception:
            parcalar = []
        for p in parcalar:
            bloklar.append(
                f"[BELGE: {p['belge_ad']} — parça {p['sira']}]\n{p['metin']}")
    if not bloklar:
        return None
    return (
        "Kullanıcının eklediği belgelerden ilgili bölümler aşağıdadır. Soruları "
        "öncelikle bu içerikle cevapla ve hangi belgeye dayandığını "
        "[BELGE: ad] biçiminde belirt. Belgede olmayanı uydurma.\n\n"
        + "\n\n".join(bloklar)
    )


@app.post("/api/sohbet")
def sohbet():
    """
    Gövde: {model, messages:[{role, content, images?:[base64,...]}], options?}
    Yanıt: NDJSON akışı — her satır Ollama'nın chunk'ı.
    Son satırda eval_count/eval_duration gibi istatistikler bulunur.
    """
    istek = request.get_json(silent=True) or {}
    mesajlar = istek.get("messages")
    if not mesajlar:
        return jsonify({"hata": "messages alanı boş"}), 400

    model = istek.get("model") or VARSAYILAN_MODEL
    # Ekli belge varsa bağlam bloğu üret (küçük belge tam, büyük belge vektör araması)
    belge_idler = istek.get("belgeler") or []
    belge_baglam = None
    if belge_idler:
        son_soru = next(
            (m.get("content", "") for m in reversed(mesajlar)
             if m.get("role") == "user"), "")
        belge_baglam = _belge_baglami(belge_idler, son_soru)
    # Model kendi kimliğini ve güncel tarihi bilemez; sistem talimatıyla veriyoruz.
    # (İstemci kendi system mesajını gönderirse ona dokunmayız.)
    if not any(m.get("role") == "system" for m in mesajlar):
        mesajlar = [{
            "role": "system",
            "content": (
                "Sen Moralite İstihbarat Modülü'nün asistanısın. Altyapın: Qwen3.5 9B "
                "(Alibaba'nın açık modeli, Mart 2026), bu bilgisayarda Ollama ile tamamen "
                f"yerel çalışıyorsun. Bugünün tarihi: {date.today().isoformat()}. "
                "Eğitim verin bu tarihten eski olduğu için güncel olayları bilmezsin; "
                "güncel bilgi sorulursa kullanıcıya arayüzdeki Web İstihbarat modunu önerebilirsin. "
                "Türkçe, net ve doğru cevap ver; emin olmadığını uydurma."
            ),
        }] + mesajlar
    if belge_baglam:
        # Belge bağlamı, baştaki sistem mesaj(lar)ından hemen sonra girer
        ilk_normal = next(
            (i for i, m in enumerate(mesajlar) if m.get("role") != "system"),
            len(mesajlar))
        mesajlar = (mesajlar[:ilk_normal]
                    + [{"role": "system", "content": belge_baglam}]
                    + mesajlar[ilk_normal:])
    govde = {
        "model": model,
        "messages": mesajlar,
        "stream": True,
        # Varsayılanlar istemci seçenekleriyle BİRLEŞTİRİLİR (yer değiştirmez);
        # aksi halde num_predict gönderen istemci temperature varsayılanını kaybeder.
        "options": {
            # belge bağlamı varsa pencere büyütülür
            "num_ctx": 16384 if belge_baglam else 8192,
            "temperature": 0.3,
            **(istek.get("options") or {}),
        },
    }
    # Düşünme yalnızca istemci isterse açılır (arayüzdeki "Derin Düşünme" anahtarı);
    # varsayılan kapalı ki cevaplar beklenmedik uzamasın.
    if "thinking" in model_yetenekleri(model):
        govde["think"] = bool(istek.get("think"))

    def akis():
        try:
            with requests.post(
                f"{OLLAMA_URL}/api/chat", json=govde, stream=True, timeout=(10, 600)
            ) as r:
                if r.status_code != 200:
                    yield json.dumps({"hata": f"Ollama {r.status_code}: {r.text[:200]}"}) + "\n"
                    return
                for satir in r.iter_lines():
                    if not satir:
                        continue
                    metin = satir.decode("utf-8")
                    # Ollama üretim ortasında hata verirse {"error": ...} yayınlar;
                    # istemcinin anladığı {"hata": ...} biçimine çevir
                    try:
                        parca = json.loads(metin)
                    except ValueError:
                        parca = None
                    if isinstance(parca, dict) and "error" in parca:
                        yield json.dumps({"hata": str(parca["error"])}) + "\n"
                    else:
                        yield metin + "\n"
        except requests.RequestException as e:
            yield json.dumps({"hata": f"Bağlantı hatası: {e}"}) + "\n"

    return Response(akis(), mimetype="application/x-ndjson")


@app.post("/api/istihbarat")
def istihbarat():
    """
    Web İstihbarat: son kullanıcı mesajını alır, web'de arar, kaynaklarla
    atıflı cevap ürettirir. Yanıt NDJSON akışı:
      {"olay": {...}}          — ilerleme (arama/kaynak) satırları
      Ollama chat chunk'ları   — sentez akışı (sohbet ucuyla aynı biçim)
    """
    istek = request.get_json(silent=True) or {}
    mesajlar = istek.get("messages") or []
    soru = next(
        (m.get("content", "") for m in reversed(mesajlar) if m.get("role") == "user"), ""
    ).strip()
    if not soru:
        return jsonify({"hata": "soru bulunamadı"}), 400
    model = istek.get("model") or VARSAYILAN_MODEL
    return Response(_istihbarat_akisi(soru, model), mimetype="application/x-ndjson")


@app.post("/api/brifing")
def brifing():
    """Günlük KAP brifingi: dün+bugün bildirimleri + model özeti + otomatik Excel."""
    soru = ("KAP günlük brifingi hazırla: dün ve bugün yayınlanan tüm bildirimleri "
            "şirket bazında özetle, önem sırasına koy, dikkat çeken gelişmeleri vurgula.")
    model = (request.get_json(silent=True) or {}).get("model") or VARSAYILAN_MODEL
    return Response(_istihbarat_akisi(soru, model, otomatik_rapor=True),
                    mimetype="application/x-ndjson")


def _istihbarat_akisi(soru, model, otomatik_rapor=False):
    def akis():
        try:
            tip = "web"
            if kap_analiz.kap_niyeti(soru):
                tip = "kap"
                # KAP soruları web aramasına gitmez: doğrudan resmi kaynaktan
                kaynaklar, uyari, etiket = [], "", ""
                for olay in kap_analiz.bildirim_akisi(soru):
                    if olay.get("tip") == "_sonuc":
                        kaynaklar = olay["kaynaklar"]
                        uyari, etiket = olay["uyari"], olay["etiket"]
                    else:
                        yield json.dumps({"olay": olay}) + "\n"
                mesaj_listesi = kap_analiz.sentez_mesajlari(soru, kaynaklar, etiket, uyari)
            else:
                sorgular = web_istihbarat.sorgu_uret(OLLAMA_URL, HIZLI_MODEL, soru)
                yield json.dumps({"olay": {"tip": "sorgular", "sorgular": sorgular}}) + "\n"
                kaynaklar, olaylar = web_istihbarat.istihbarat_topla(soru, sorgular)
                for o in olaylar:
                    yield json.dumps({"olay": o}) + "\n"
                # 2. tur kararı: hiç kaynak yoksa kesin; varsa yeterlilik kontrolü
                if not kaynaklar:
                    tur2 = web_istihbarat.sorgu_uret(
                        OLLAMA_URL, HIZLI_MODEL, soru, onceki=sorgular)
                else:
                    yeterli, oneriler = web_istihbarat.yeterlilik_kontrol(
                        OLLAMA_URL, HIZLI_MODEL, soru, kaynaklar)
                    tur2 = oneriler if not yeterli else []
                if tur2:
                    yield json.dumps({"olay": {"tip": "tur2", "sorgular": tur2}}) + "\n"
                    k2, _ = web_istihbarat.istihbarat_topla(soru, tur2)
                    mevcut = {k["url"] for k in kaynaklar}
                    for k in k2:
                        if k["url"] not in mevcut and len(kaynaklar) < 6:
                            k["no"] = len(kaynaklar) + 1
                            kaynaklar.append(k)
                            yield json.dumps({"olay": {
                                "tip": "kaynak", "no": k["no"],
                                "baslik": k["baslik"], "url": k["url"]}}) + "\n"
                mesaj_listesi = web_istihbarat.sentez_mesajlari(soru, kaynaklar)
            yield json.dumps({"olay": {"tip": "sentez", "kaynak_sayisi": len(kaynaklar)}}) + "\n"

            govde = {
                "model": model,
                "messages": mesaj_listesi,
                "stream": True,
                "options": {"num_ctx": 16384, "temperature": 0.3},
            }
            if "thinking" in model_yetenekleri(model):
                govde["think"] = False
            with requests.post(
                f"{OLLAMA_URL}/api/chat", json=govde, stream=True, timeout=(10, 600)
            ) as r:
                if r.status_code != 200:
                    yield json.dumps({"hata": f"Ollama {r.status_code}: {r.text[:200]}"}) + "\n"
                    return
                cevap_parcalari = []
                for satir in r.iter_lines():
                    if not satir:
                        continue
                    metin = satir.decode("utf-8")
                    try:
                        parca = json.loads(metin)
                    except ValueError:
                        parca = None
                    if isinstance(parca, dict) and "error" in parca:
                        yield json.dumps({"hata": str(parca["error"])}) + "\n"
                    else:
                        if isinstance(parca, dict):
                            icerik = (parca.get("message") or {}).get("content")
                            if icerik:
                                cevap_parcalari.append(icerik)
                        yield metin + "\n"
            # Kaynak listesini istemciye son bir olayla bildir (balon altına yazılır)
            if kaynaklar:
                yield json.dumps({"olay": {"tip": "kaynakca", "kaynaklar": [
                    {"no": k["no"], "baslik": k["baslik"], "url": k["url"]} for k in kaynaklar
                ]}}) + "\n"
            # Rapor Motoru için son çalışmayı sakla
            SON_ISTIHBARAT["veri"] = {
                "soru": soru,
                "cevap": "".join(cevap_parcalari).strip(),
                "kaynaklar": kaynaklar,
                "tip": tip,
                "zaman": datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            if otomatik_rapor and SON_ISTIHBARAT["veri"]["cevap"]:
                try:
                    ad = rapor_motoru.excel_uret(SON_ISTIHBARAT["veri"])
                    yield json.dumps({"olay": {"tip": "rapor", "dosya": ad,
                                               "url": f"/raporlar/{ad}"}}) + "\n"
                except Exception as e:
                    yield json.dumps({"hata": f"rapor üretilemedi: {e}"}) + "\n"
        except Exception as e:  # modül hatası kullanıcıya açık iletilsin
            yield json.dumps({"hata": f"İstihbarat hattı hatası: {e}"}) + "\n"

    return akis()


@app.post("/api/rapor")
def rapor():
    """Son istihbarat/KAP çalışmasını biçimli Excel raporuna döker."""
    veri = SON_ISTIHBARAT["veri"]
    if not veri:
        return jsonify({"hata": "Henüz rapor edilecek istihbarat çalışması yok — "
                                "önce Web İstihbarat modunda bir soru sorun."}), 400
    try:
        ad = rapor_motoru.excel_uret(veri)
    except Exception as e:
        return jsonify({"hata": f"rapor üretilemedi: {e}"}), 500
    return jsonify({"dosya": ad, "url": f"/raporlar/{ad}"})


@app.get("/raporlar/<path:ad>")
def rapor_indir(ad):
    return send_from_directory(rapor_motoru.KLASOR, ad, as_attachment=True)


if __name__ == "__main__":
    print(f"Moralite arayüzü: http://localhost:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
