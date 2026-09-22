# Playground JSON'ları

Aynı 10 senaryonun [Jev Playground](https://typesafe.ai) versiyonu. Her senaryo için
iki dosya var; içeriği olduğu gibi kopyalayıp ilgili panoya yapıştır:

| Pano | Dosya |
|---|---|
| **State** (üst) | `NN_<ad>.state.json` |
| **Questions** (alt) | `NN_<ad>.questions.json` |

`03_masak_supheli_islem` toplu tarama senaryosu olduğu için üç ayrı state dosyası var
(`state_1`, `state_2`, `state_3`) — aynı soru setini üç müşteri kaydıyla sırayla dene,
cevaplar arasındaki farkı gör: 1 = para katiri deseni, 2 = ekonomik gerekçesi olan
ticari akış (yanlış pozitif kontrolü), 3 = nakit yatırma + kripto çıkışı.

`tum_senaryolar.json` hepsini tek dosyada toplar:

```json
{ "01_kart_itirazi_chargeback": { "baslik": "...", "state": {...}, "questions": {...} }, ... }
```

Bu dosya API'ye doğrudan beslenebilir:

```python
import json
from typesafe_sdk import TypeSafeClient

senaryolar = json.load(open("jev/playground/tum_senaryolar.json"))
s = senaryolar["02_eft_oncesi_dolandiricilik"]

with TypeSafeClient() as client:                    # sorular ham dict olarak da kabul edilir
    yanit = client.system_one(state=s["state"], questions=s["questions"])
```

Not: Playground'da karar mantığı yok — orada sadece olasılıkları görürsün. Eşikler ve
birleştirme (`p > 0.7`, `score >= 1.5`, düşük güvende insana yönlendirme) bir üst
klasördeki Python dosyalarında duruyor.
