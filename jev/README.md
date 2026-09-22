# Jev (TypeSafe AI) deneme senaryoları — bankacılık

Her dosya **tek parça**: kendi `API_KEY`/`PROXY` satırı, kendi soruları, kendi karar
mantığı ve kendi hata yakalaması var. Hiçbir dosya diğerini import etmez — dosyanın
tamamını bir Colab hücresine yapıştırıp çalıştırabilirsin.

Ortak kalıp: model *tek bir dar hüküm* verir (bu metin şu kalıba uyuyor mu?), ürün/limit/
mevzuat kuralı Python tarafında kalır. Böylece eşik değiştiğinde prompt değil kod değişir.

## Colab'da çalıştırma

İlk hücre:

```python
!pip install -q typesafe-sdk
```

`pydantic` sürüm uyarısı çıkarsa **Çalışma zamanını yeniden başlat** deyip devam et.

Anahtar için iki yol var:

- Dosyadaki `API_KEY = ""` satırına yapıştır, veya
- Colab'ın sol menüsündeki 🔑 **Secrets** bölümüne `TYPESAFE_API_KEY` adıyla ekle,
  "Notebook access" anahtarını aç. Dosyadaki `anahtar()` fonksiyonu `API_KEY` boşsa
  önce Colab Secrets'a, o da yoksa `TYPESAFE_API_KEY` ortam değişkenine bakar.

Sonra senaryo dosyasının tamamını ikinci hücreye yapıştır ve çalıştır.

## Yerelde çalıştırma

```bash
pip install typesafe-sdk
export TYPESAFE_API_KEY="ts-..."
python jev/01_kart_itirazi_chargeback.py
```

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

## PyQt uygulaması — `jev_pyqt.py`

Aynı 10 senaryo gömülü gelen bir masaüstü arayüz; ayrıca dışarıdan JSON talimat yükler.

```bash
pip install typesafe-sdk PyQt6      # PyQt5 de çalışır
python jev/jev_pyqt.py
python jev/jev_pyqt.py talimat.json # doğrudan bir talimatla açmak için
```

- Soldaki listeden senaryo seç; **State** ve **Questions** panolarını düzenleyebilirsin —
  gönderilen şey ekranda gördüğündür.
- **Çalıştır** (Ctrl+Enter) isteği ayrı bir iş parçacığında atar, arayüz donmaz.
- Cevaplar olasılık çubuklarıyla gösterilir; gömülü senaryolarda eşik/karar bloğu da çalışır.
- **JSON yükle…** (ya da dosyayı pencereye sürükle-bırak) — biçim otomatik algılanır:

| Yüklenen JSON | Nasıl yorumlanır |
|---|---|
| `{"state": {...}, "questions": {...}}` | tek senaryo (`baslik`, `aciklama` varsa kullanılır) |
| `{"ad": {"baslik", "state", "questions"}, ...}` | çoklu senaryo — `tum_senaryolar.json` biçimi |
| `{"soru_adi": {"type": "noul", ...}, ...}` | yalnızca soru seti; state'i sen doldurursun |
| başka her nesne/dizi | yalnızca state |

Çoklu senaryo dosyasında `state` bir dizi ise (03'teki üç MASAK kaydı gibi) her eleman
ayrı senaryo olarak listeye girer. **JSON kaydet…** ile düzenlediğin panoları
`{"baslik", "state", "questions"}` olarak dışarı alırsın — o dosya tekrar yüklenebilir.

Anahtar: üstteki alana yaz, ya da `TYPESAFE_API_KEY` ortam değişkeni; dosya başındaki
`API_KEY` satırı da çalışır.

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
- `client.system_one(..., model="...")` ile farklı modelleri aynı senaryoda karşılaştır;
  hesabın modellerini `client.models.list()` ile görebilirsin.
- Aynı senaryoyu 5 kez çağırıp olasılıkların oynaklığını (kararlılık) ölç.
- Kritik senaryolarda (02, 07, 10) sahte "temiz" bir state yazıp yanlış pozitif ver mi diye dene.
