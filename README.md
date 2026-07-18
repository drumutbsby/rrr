# Moralite — İstihbarat Modülü

Yerel (kapalı devre çalışabilen) LLM tabanlı analiz ve istihbarat platformu.
Uzun vadeli hedef: KAP dahil birden çok kaynaktan bilgi toplayıp rapor üreten geniş kapsamlı motor.

## Mimari

```
moralite/
  app.py               # Flask sunucusu — Ollama'ya akışlı köprü (port 8770)
  static/index.html    # Sohbet arayüzü (tek dosya, CDN'siz, çevrimdışı çalışır)
  Modelfile            # kap-asistan model tanımı (ollama create ile)
  moduller/            # Gelecek modüller (web istihbarat, rapor motoru...)
  test-resim.png       # Vision testi için örnek görsel
```

## Kurulum ve çalıştırma

1. [Ollama](https://ollama.com) kurulu ve çalışıyor olmalı; model: `ollama pull qwen3.5:9b`
   (belge bilgi tabanı için ayrıca `ollama pull bge-m3`).
2. `pip install -r requirements.txt`
3. `python app.py`
4. Tarayıcıda `http://localhost:8770`

> **Not:** KAP Analiz modülü, [ccdene1 KAP Risk projesinin](../ccdene1) çekirdeğini
> (`kap_risk_app.py`) yerel diskten import eder (`moduller/kap_analiz.py` içindeki
> `CEKIRDEK_YOL`). O proje yoksa KAP soruları çalışmaz; diğer tüm özellikler bağımsızdır.

## Modeller

| Model | Rol |
|---|---|
| `qwen3.5:9b` | Tek model: sohbet + görüntü + belge + web sorgu üretimi + sentez (Mart 2026 nesli) |

> `Modelfile` dosyası, ileride KAP'a özel kurallı bir model gerekirse şablon olarak duruyor
> (temel modeli `FROM qwen3.5:9b` yapıp `ollama create kap-asistan -f Modelfile` ile üretilir).

## Yol haritası

- [x] Yerel model + sohbet arayüzü + görüntü analizi
- [x] Web İstihbarat modülü (sorgu üret → DuckDuckGo → sayfa ayıkla → atıflı sentez)
- [x] KAP Analiz modülü (web modunda KAP soruları otomatik olarak ccdene1 çekirdeği
      üzerinden resmî KAP verisinden cevaplanır; "dün/bugün" ve hisse kodu algılar)
- [ ] Rapor Motoru (toplanan veriden Excel/PDF rapor)

> Yatırım tavsiyesi değildir. Model çıktıları hata içerebilir; kritik veri her zaman kaynağından doğrulanmalı.
