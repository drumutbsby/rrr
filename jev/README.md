# Jev (TypeSafe AI) deneme senaryoları — bankacılık

Her dosya tek başına çalışan bir senaryo: gerçek bir bankacılık kararı, o karara
yetecek dar sorular ve **eşikleri/birleştirmeyi kodda tutan** bir karar bloğu.

Ortak kalıp: model *tek bir hüküm* verir (bu metin şu kalıba uyuyor mu?), ürün/limit/
mevzuat kuralı Python tarafında kalır. Böylece eşik değiştiğinde prompt değil kod değişir.

## Kurulum

```bash
pip install typesafe-sdk
export TYPESAFE_API_KEY="ts-..."        # veya jev/ortak.py içindeki API_KEY satırına yaz
python jev/01_kart_itirazi_chargeback.py
```

Anahtar, proxy ve model ayarı tek yerde: [`ortak.py`](ortak.py). Senaryolar bu dosyadan
`sor()` (tek çağrı), `istemci()` (bağlantıyı yeniden kullanan çağrılar), `yazdir()` ve
`karar()` yardımcılarını alır. Hata mesajları (yanlış anahtar, proxy, zaman aşımı, hız
limiti) `calistir()` içinde Türkçeleştirilmiştir.

## Senaryolar

| # | Dosya | Karar | Öne çıkan kullanım |
|---|---|---|---|
| 01 | `01_kart_itirazi_chargeback.py` | Ters ibraz açılsın mı, hangi gerekçe kodundan? | 120 gün kuralı + kalıp→şema kodu eşlemesi kodda |
| 02 | `02_eft_oncesi_dolandiricilik.py` | Yüksek tutarlı FAST durdurulsun mu? | Zayıf sinyalleri sayarak birleştirme (`ikna_gostergesi`) |
| 03 | `03_masak_supheli_islem.py` | Hangi hesap ŞİB adayı, analist kuyruğu sırası? | Tek istemci ile **toplu** tarama + skora göre sıralama |
| 04 | `04_kobi_kredi_on_degerlendirme.py` | Dosya tahsise gitsin mi, hangi yetki kademesine? | Metin–tablo tutarlılığı; rasyolar (DSCR, borç/özkaynak) kodda |
| 05 | `05_ifrs9_erken_uyari.py` | Kredi 2. aşamaya (yakın izleme) alınsın mı? | `response_model` ile **tip güvenli** cevap alanları |
| 06 | `06_tahsilat_gorusmesi.py` | Yapılandırma mı, hukuki takip mi? | Hassas müşteri koruması + uygunsuz tahsilat dili denetimi |
| 07 | `07_sim_swap_hesap_ele_gecirme.py` | Kanallar kapatılsın mı? | Telemetri ile beyanın çapraz kontrolü; arayanın kendisi şüpheli olabilir |
| 08 | `08_yapilandirma_talebi.py` | Hangi çözüm ürünü teklif edilsin? | Ürün uygunluk matrisi kodda (`URUN_KURALI`) |
| 09 | `09_uzaktan_kimlik_tespiti_kyc.py` | Hesap açılışı tamamlansın mı? | Video tutanağından yönlendirme/vekâleten hesap tespiti, PEP |
| 10 | `10_gise_nakit_cekim_baski.py` | Nakit teslim edilsin mi? | Baskı altındaki müşteri; "güvenli hesap" anlatısı tek başına durdurucu |

## Senaryo yazarken izlenen kurallar

1. **Bir soru = bir hüküm.** "Riskli mi?" değil; "müşteri işlemi kendisi yapmadığını
   söylüyor mu?" Birden çok hüküm tek soruya sıkıştırılırsa olasılık yorumlanamaz hâle gelir.
2. **`Noul` sinyal, `Choice` yönlendirme, `Score` şiddet içindir.** Aciliyet/risk gibi
   kademeli şeyler `Score`; ekip/ürün/gerekçe kodu gibi ayrık şeyler `Choice`.
3. **Kritik olumsuzlar ayrı sorulur.** "Ekonomik gerekçe var mı?" gibi bir doğrulayıcı
   soru, yanlış pozitifleri kodda törpülemeyi sağlar.
4. **Güven düşükse insana gider.** Her senaryoda `confidence < 0.55–0.60` eşiği ile
   manuel kuyruk yolu vardır; model emin değilken karar vermez.
5. **Sorular İngilizce, veri Türkçe.** Metin (state) Türkçe kalır; hüküm cümleleri
   İngilizce yazıldığında kriterler daha kararlı sonuç veriyor. Aynı soru setini
   Türkçeleştirip karşılaştırmak iyi bir deney.
6. **Mevzuat kodda.** 120 gün, 1.25 DSCR, 30 gün gecikme, limit eşikleri — hiçbiri
   prompt içinde değil; değiştiğinde tek satır güncellenir.

## Denemeye değer varyasyonlar

- Aynı `STATE` üzerinde eşikleri oynatıp kaç dosyanın insana düştüğünü ölç.
- `state`'i düz metin yerine yapılandırılmış JSON verip (04, 05) fark var mı bak.
- `ortak.MODEL` ile farklı modelleri aynı senaryoda karşılaştır.
- Aynı senaryoyu 5 kez çağırıp olasılıkların oynaklığını (kararlılık) ölç.
- Kritik senaryolarda (02, 07, 10) sahte "temiz" bir state yazıp yanlış pozitif ver mi diye dene.
