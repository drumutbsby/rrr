# -*- coding: utf-8 -*-
"""
Moralite — KAP Analiz modülü.

KAP verisini genel web aramasıyla DEĞİL, ccdene1 projesindeki kanıtlanmış
çekirdekle (kap_risk_app) doğrudan KAP'tan çeker: üye rehberi, yıl bazlı
bildirim sorgusu, hız sınırlayıcı ve önbellek çekirdekten miras alınır.
"""
import os
import re
import sys
from datetime import date, timedelta

CEKIRDEK_YOL = r"C:\Users\MSİ\Desktop\ccdene1"
if CEKIRDEK_YOL not in sys.path:
    sys.path.insert(0, CEKIRDEK_YOL)
import kap_risk_app as cekirdek  # noqa: E402  (KAP veri katmanı tek kaynaktan)

_KAP_KELIME = re.compile(r"\bkap\b", re.IGNORECASE)
_KONU_KELIMELERI = ("bildirim", "özel durum", "ozel durum", "açıklama",
                    "aciklama", "duyuru", "aciklamalar", "açıklamalar")


def kap_niyeti(soru: str) -> bool:
    """Soru KAP bildirimlerini mi istiyor? (web araması yerine KAP hattı)"""
    s = soru.lower()
    return bool(_KAP_KELIME.search(s)) and any(k in s for k in _KONU_KELIMELERI)


def gun_araligi(soru: str):
    """Sorudaki görece tarihi (dün/bugün) gerçek aralığa çevirir."""
    s = soru.lower()
    bugun = date.today()
    if ("dün" in s or "dun" in s) and ("bugün" in s or "bugun" in s):
        d = bugun - timedelta(days=1)
        return d, bugun, f"dün + bugün ({d.isoformat()} → {bugun.isoformat()})"
    if "dün" in s or "dun" in s:
        d = bugun - timedelta(days=1)
        return d, d, "dün (" + d.isoformat() + ")"
    if "bugün" in s or "bugun" in s:
        return bugun, bugun, "bugün (" + bugun.isoformat() + ")"
    d = bugun - timedelta(days=2)
    return d, bugun, f"son 3 gün ({d.isoformat()} → {bugun.isoformat()})"


def _uyeleri_sec(soru: str, directory):
    """Soruda hisse kodu geçiyorsa onları, yoksa varsayılan izleme evrenini seçer."""
    adaylar = set(re.findall(r"\b[A-ZÇĞİÖŞÜ]{3,6}\b", soru))
    adaylar.discard("KAP")  # platformun adı hisse kodu değil
    uyeler, secilen_kodlar = [], []
    for row in directory.itertuples():
        kodlar = set(str(row.kodlar).split(","))
        istenen = kodlar & adaylar
        if istenen:
            uyeler.append({"hisse": row.hisse, "unvan": row.unvan,
                           "oid": row.oid, "islem": row.islem})
            secilen_kodlar.extend(istenen)
    if uyeler:
        return uyeler, ", ".join(sorted(secilen_kodlar))
    # resolve_default_members → (oid listesi, eşleşmeyen terimler); oid'leri
    # rehber satırlarına geri eşleyerek üye sözlükleri kurulur
    oid_liste, _ = cekirdek.resolve_default_members(directory)
    oid_kume = set(oid_liste)
    uyeler = [{"hisse": row.hisse, "unvan": row.unvan,
               "oid": row.oid, "islem": row.islem}
              for row in directory.itertuples() if row.oid in oid_kume]
    return uyeler, "varsayılan izleme listesi (" + str(len(uyeler)) + " şirket)"


def bildirim_akisi(soru: str):
    """
    Üreteç: ilerleme olayları ve sonuçlar akar.
      {"tip": "arama", ...}   — tarama başlığı
      {"tip": "kaynak", ...}  — şirket bazında bulunan bildirim sayısı
    Bittiğinde StopIteration.value yerine son olay olarak
      {"tip": "_sonuc", "kaynaklar": [...], "uyari": "..."} yayınlanır.
    """
    bas, son, etiket = gun_araligi(soru)
    directory = cekirdek.fetch_member_directory()
    uyeler, kapsam = _uyeleri_sec(soru, directory)
    yield {"tip": "arama", "sorgu": f"KAP taraması: {kapsam} · {etiket}"}

    kaynaklar, basarisiz = [], []
    yillar = tuple(sorted({bas.year, son.year}))
    for uye in uyeler:
        bildirimler, hata = cekirdek.fetch_company_disclosures(uye["oid"], yillar)
        if hata:
            basarisiz.append(uye["hisse"])
        gunun = []
        for b in bildirimler:
            try:
                t = cekirdek.parse_date(b.get("publishDate", "")).date()
            except Exception:
                continue
            if bas <= t <= son:
                gunun.append(b)
        if gunun:
            yield {"tip": "kaynak", "no": len(kaynaklar) + 1,
                   "baslik": f"{uye['hisse']}: {len(gunun)} bildirim",
                   "url": f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{uye['oid']}"}
        for b in gunun:
            kaynaklar.append({
                "no": len(kaynaklar) + 1,
                "baslik": f"{uye['hisse']} — {(b.get('title') or b.get('subject') or '?')[:90]}",
                "url": f"https://www.kap.org.tr/tr/Bildirim/{b.get('disclosureIndex')}",
                "ozet": (b.get("summary") or "")[:300],
                "metin": "\n".join(filter(None, [
                    f"Şirket: {b.get('companyTitle') or uye['unvan']}",
                    f"Hisse: {uye['hisse']}",
                    f"Tarih: {b.get('publishDate', '')[:16]}",
                    f"Tür: {b.get('ruleTypeTerm') or '-'}",
                    f"Başlık: {b.get('title') or '-'}",
                    f"Özet: {b.get('summary') or '-'}",
                ])),
            })

    uyari = ""
    if basarisiz:
        # Sessiz veri kaybı yok: alınamayan şirketler açıkça bildirilir
        uyari = "Veri alınamayan şirketler (KAP kısıtlaması olabilir): " + ", ".join(basarisiz)
    yield {"tip": "_sonuc", "kaynaklar": kaynaklar, "uyari": uyari, "etiket": etiket}


def sentez_mesajlari(soru: str, kaynaklar: list, etiket: str, uyari: str):
    """Ana modele gidecek mesajlar — KAP bağlamına özel sistem talimatı."""
    if kaynaklar:
        blok = "\n\n".join(
            f"[KAYNAK {k['no']}]\n{k['metin']}\nLink: {k['url']}" for k in kaynaklar
        )
        sistem = (
            f"Sen Moralite'nin KAP analistisin. Bugünün tarihi: {date.today().isoformat()}. "
            "Aşağıdaki bildirimler az önce doğrudan KAP'tan (resmi platform) çekildi. "
            "Bildirimleri şirket bazında grupla, önemli görünenleri (finansal rapor, "
            "özel durum, ertelemeler, yönetim değişiklikleri) öne al ve tek cümlelik "
            "yorum ekle. Atıfları [1], [2] biçiminde yaz. Uydurma bilgi ekleme; "
            "yatırım tavsiyesi verme."
        )
        kullanici = f"{blok}\n\n---\nSORU: {soru}\n(Kapsanan aralık: {etiket})"
        if uyari:
            kullanici += f"\nNOT: {uyari} — cevabında bunu belirt."
    else:
        sistem = (
            f"Sen Moralite'nin KAP analistisin. Bugünün tarihi: {date.today().isoformat()}. "
            "KAP taraması yapıldı ancak istenen aralıkta bildirim bulunamadı. Bunu net "
            "söyle; izleme listesindeki şirketlerde o gün bildirim olmayabilir. Türkçe cevap ver."
        )
        kullanici = f"SORU: {soru}\n(Taranan aralık: {etiket}; sonuç: 0 bildirim. {uyari})"
    return [
        {"role": "system", "content": sistem},
        {"role": "user", "content": kullanici},
    ]
