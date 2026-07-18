# -*- coding: utf-8 -*-
"""
Moralite — Web İstihbarat modülü.

Deterministik boru hattı (küçük modellerde ajans döngüsünden daha güvenilir):
  1. Hızlı model arama sorguları üretir
  2. DuckDuckGo'da aranır (API anahtarı gerekmez)
  3. En iyi sayfalar indirilir, ana metin ayıklanır
  4. Ana model, kaynaklarla birlikte atıflı cevap üretir (akışlı)
"""
import json
import re
from datetime import date

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SAYFA_KARAKTER_SINIRI = 4000
KAYNAK_SAYISI = 4


def ara(sorgu, adet=6):
    """DuckDuckGo metin araması. [{title, href, body}] döner."""
    try:
        with DDGS() as d:
            return list(d.text(sorgu, region="tr-tr", max_results=adet))
    except Exception:
        return []


def sayfa_metni(url, zaman_asimi=12):
    """Sayfayı indirip ana metni ayıklar; hata olursa None döner."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=zaman_asimi)
        r.raise_for_status()
        if "text/html" not in r.headers.get("Content-Type", "text/html"):
            return None
        corba = BeautifulSoup(r.text, "html.parser")
        for etiket in corba(["script", "style", "nav", "header", "footer", "aside", "form"]):
            etiket.decompose()
        govde = corba.find("article") or corba.find("main") or corba.body or corba
        metin = re.sub(r"\n{3,}", "\n\n", govde.get_text("\n", strip=True))
        return metin[:SAYFA_KARAKTER_SINIRI] if metin.strip() else None
    except Exception:
        return None


def sorgu_uret(ollama_url, hizli_model, soru, onceki=None):
    """Hızlı modelle 1-2 arama sorgusu üretir; başarısız olursa soruyu aynen kullanır.
    `onceki` verilirse (2. tur) farklı açıdan sorgular istenir."""
    tur2_notu = ""
    if onceki:
        tur2_notu = (
            f"İLK DENEME BAŞARISIZ OLDU (şu sorgular sonuç vermedi: {', '.join(onceki)}). "
            "Bu kez FARKLI bir açıdan yaklaş: eş anlamlılar, daha genel/daha özgül ifade "
            "veya İngilizce varyant dene. "
        )
    istem = (
        f"Bugünün tarihi: {date.today().isoformat()}. Aşağıdaki soru için web araması yapılacak. "
        f"{tur2_notu}"
        "Bir insanın arama motoruna yazacağı gibi 2 kısa ve isabetli sorgu üret. Kurallar: "
        "kısaltmaları aç (örn. KAP → Kamuyu Aydınlatma Platformu), 'dün/bugün' gibi görece "
        "tarihleri gerçek tarihe çevir, teknik/API terimleri EKLEME — haber ve resmi kaynak "
        "bulmaya odaklan. "
        "SADECE şu JSON'u döndür, başka hiçbir şey yazma: {\"sorgular\": [\"...\", \"...\"]}\n\n"
        f"Soru: {soru}"
    )
    try:
        r = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": hizli_model, "prompt": istem, "stream": False,
                  # qwen3.5 gibi düşünen modellerde bütçe düşünmeye gitmesin
                  "think": False,
                  "format": "json", "options": {"num_predict": 120, "temperature": 0.2}},
            timeout=90,
        )
        r.raise_for_status()
        sorgular = json.loads(r.json().get("response", "{}")).get("sorgular", [])
        sorgular = [s.strip() for s in sorgular if isinstance(s, str) and s.strip()]
        return sorgular[:2] or [soru]
    except Exception:
        return [soru]


def yeterlilik_kontrol(ollama_url, model, soru, kaynaklar):
    """Toplanan kaynaklar soruyu cevaplamaya yeterli mi?
    → (yeterli: bool, yeni_sorgular: list). Kontrol başarısız olursa (True, [])
    döner ki tek turla devam edilsin — kontrol hattı asla akışı kilitlemesin."""
    if not kaynaklar:
        return False, []
    ozetler = "\n".join(
        f"- {k['baslik']}: {(k['ozet'] or k['metin'])[:150]}" for k in kaynaklar)
    istem = (
        f"Bugün {date.today().isoformat()}. SORU: {soru}\n\n"
        f"ELDEKİ KAYNAK ÖZETLERİ:\n{ozetler}\n\n"
        "Bu kaynaklar soruyu doğru ve güncel cevaplamak için yeterli mi? Yetersizse "
        "farklı açıdan 2 yeni arama sorgusu öner. SADECE şu JSON'u döndür: "
        '{"yeterli": true, "yeni_sorgular": []}'
    )
    try:
        r = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": istem, "stream": False, "think": False,
                  "format": "json", "options": {"num_predict": 150, "temperature": 0.2}},
            timeout=120,
        )
        r.raise_for_status()
        j = json.loads(r.json().get("response", "{}"))
        yeni = [s.strip() for s in (j.get("yeni_sorgular") or [])
                if isinstance(s, str) and s.strip()][:2]
        return bool(j.get("yeterli", True)), yeni
    except Exception:
        return True, []


def istihbarat_topla(soru, sorgular):
    """Arar, sayfaları indirir. (kaynaklar, olay_akisi) döner.

    kaynaklar: [{no, baslik, url, ozet, metin}]
    olay üreteci olarak da kullanılabilsin diye adım listesi döndürür.
    """
    olaylar = []
    gorulen, adaylar = set(), []
    for sorgu in sorgular:
        olaylar.append({"tip": "arama", "sorgu": sorgu})
        for sonuc in ara(sorgu):
            url = sonuc.get("href")
            if url and url not in gorulen:
                gorulen.add(url)
                adaylar.append(sonuc)

    kaynaklar = []
    for aday in adaylar:
        if len(kaynaklar) >= KAYNAK_SAYISI:
            break
        metin = sayfa_metni(aday["href"])
        if metin:
            kaynaklar.append({
                "no": len(kaynaklar) + 1,
                "baslik": aday.get("title", "?"),
                "url": aday["href"],
                "ozet": aday.get("body", ""),
                "metin": metin,
            })
            olaylar.append({"tip": "kaynak", "no": len(kaynaklar),
                            "baslik": aday.get("title", "?"), "url": aday["href"]})
    return kaynaklar, olaylar


def sentez_mesajlari(soru, kaynaklar):
    """Ana modele gidecek mesaj listesini kurar."""
    if kaynaklar:
        blok = "\n\n".join(
            f"[KAYNAK {k['no']}] {k['baslik']} ({k['url']})\n{k['metin']}"
            for k in kaynaklar
        )
        sistem = (
            f"Sen Moralite'nin web istihbarat analistisin. Bugünün tarihi: {date.today().isoformat()}. "
            "Aşağıdaki KAYNAK metinleri az önce "
            "internetten toplandı ve günceldir; kendi eski bilginle çelişirse KAYNAKLARI esas al. "
            "Türkçe, net ve yapılandırılmış cevap ver. Her önemli iddianın sonuna [1], [2] gibi "
            "kaynak numarası koy. Kaynaklarda olmayan bilgiyi uydurma; bilinmiyorsa söyle. "
            "Yatırım tavsiyesi verme."
        )
        kullanici = f"{blok}\n\n---\nSORU: {soru}"
    else:
        sistem = (
            "Sen Moralite'nin web istihbarat analistisin. Web araması başarısız oldu; "
            "kullanıcıya güncel kaynak bulunamadığını açıkça söyle ve yalnızca genel bilginle, "
            "güncellik uyarısı vererek yardımcı ol. Türkçe cevap ver."
        )
        kullanici = f"SORU: {soru}"
    return [
        {"role": "system", "content": sistem},
        {"role": "user", "content": kullanici},
    ]
