# PRD — Moralite İstihbarat Modülü v1.0

> Ürün Gereksinim Dokümanı · 18 Temmuz 2026 · Sahip: Umut
> Uygulayıcı: Claude (otonom geliştirme döngüsü) · Durum işaretleri döngü tarafından güncellenir.

## 1. Vizyon

Tek kişilik, tamamen yerel çalışan bir **kişisel istihbarat platformu**: KAP + web'den bilgi
toplar, belge ve görüntü analiz eder, güncel LLM ürünlerinin (ChatGPT/Claude/Gemini arayüzleri)
temel deneyim özelliklerini yerel modelle sunar ve sonuçları rapora döker. Veri makinede kalır;
tek dış temas noktası kullanıcının açıkça başlattığı web aramalarıdır.

## 2. Mevcut durum (tamamlananlar)

Sohbet arayüzü (akışlı, koyu tema) · görüntü analizi (qwen3.5:9b) · Web İstihbarat
(sorgu üret → DuckDuckGo → ayıkla → atıflı sentez) · KAP Analiz (ccdene1 çekirdeğinden resmî
veri) · kimlik/tarih sistem talimatı · 8 bulguluk güvenlik/doğruluk inceleme turu kapalı.

## 3. Özellik listesi (öncelik sıralı)

Her madde: kabul ölçütüyle birlikte. Döngü bir maddeyi bitirince `[x]` yapar ve
"Doğrulama" satırına kanıtı yazar.

### Faz 1 — Sohbet deneyimi (güncel LLM arayüz standartları)

- [x] **1.1 Çoklu sohbet yönetimi**: Kenar çubuğunda sohbet listesi; yeni sohbet eskiyi
  silmez, adlandırılır (ilk mesajdan otomatik başlık), geçmişten seçilip devam edilir,
  silinebilir. Kalıcılık localStorage'da çoklu-anahtar düzeninde.
  Kabul: iki ayrı sohbet açılıp aralarında geçiş yapılabiliyor; sayfa yenilenince ikisi de duruyor.
  Doğrulama: 18.07.2026 — eski tek sohbet "Önceki sohbet" olarak taşındı (2 mesaj korunarak);
  yeni sohbet oluşturma/geçiş/geri dönüş tarayıcıda test edildi; sayfa yenilemesi sonrası
  2 sohbet ve aktif mesajlar kalıcı; konsol hatasız. Silme confirm() korumalı; akış
  sürerken geçiş/silme kilitli.
- [x] **1.2 Derin Düşünme anahtarı**: Kenar çubuğunda 🧠 anahtar; açıkken `think:true`
  gönderilir, düşünme içeriği balonda katlanabilir soluk blok olarak gösterilir
  (Ollama `message.thinking` alanı). Kapalıyken mevcut davranış.
  Kabul: anahtar açıkken cevapta katlanabilir düşünme bloğu görünüyor.
  Doğrulama: 18.07.2026 — API: think:true ile 528 karakter düşünme + doğru cevap (3×17=51);
  think kapalı: düşünme 0, doğru cevap (5+5=10). Arayüz anahtarı AKTİF/KAPALI geçişi test
  edildi. BONUS HATA DÜZELTMESİ: istemci options gönderince temperature varsayılanının
  kaybolduğu birleştirme hatası bulundu ve giderildi (options artık merge ediliyor) —
  bu hata matematik sorularında saçma cevaplara yol açıyordu.
- [x] **1.3 Panodan görsel yapıştırma**: Metin kutusuna Ctrl+V ile ekran görüntüsü
  yapıştırılabilir (paste olayında clipboard image → mevcut ekleme akışı).
  Kabul: pano görseli önizlemede beliriyor ve modele gidiyor.
  Doğrulama: 18.07.2026 — sentetik ClipboardEvent ile PNG yapıştırıldı: ek listesine
  girdi (PNG imzalı base64), önizlemede göründü, MIME korundu. Metin yapıştırma
  etkilenmiyor (engellenmedi, ek sayısı sabit). Dosya seçimi ve pano aynı ortak
  okuma zincirini (bekleyenOkuma) kullanıyor — gönderim yarışı yok.
- [x] **1.4 Sohbeti dışa aktar**: Aktif sohbeti Markdown dosyası olarak indir
  (kaynakçalar dahil). Kabul: indirilen .md dosyası konuşmayı eksiksiz içeriyor.
  Doğrulama: 18.07.2026 — "⬇ Sohbeti Dışa Aktar" düğmesi eklendi; üretilen Markdown
  başlık + tarih + model bilgisi + tüm kullanıcı/asistan bölümleri + kaynakça satırlarını
  içeriyor (tarayıcıda birebir doğrulandı). Ek iyileştirme: web/KAP kaynakçaları artık
  sohbet geçmişine kaydediliyor — sayfa yenilense de balonların altında görünüyor
  (modele gönderilmeden önce ayıklanıyor). Konsol hatasız. FAZ 1 TAMAMLANDI.

### Faz 2 — Belge zekâsı (RAG)

- [x] **2.1 Belge yükleme**: 📄 düğmesiyle PDF/TXT/MD yükleme; sunucu pypdf ile metni
  çıkarır. Kabul: yüklenen PDF'in metni çıkarılıp önizlemede "N sayfa, M karakter" görünüyor.
  Doğrulama: 18.07.2026 — /api/belge ucu + 📄 düğmesi + belge çipleri (sayfa/karakter
  gösterimli). PDF metni pypdf ile çıkarıldı ("gizli kod ZX-77" testi geçti); belgeler
  `belgeler/<id>.json` olarak kalıcı; sohbet başına belge listesi localStorage'da.
- [x] **2.2 Belgeyle sohbet (tek belge, bağlam-içi)**: Küçük belgeler (≤ ~12k token)
  doğrudan bağlama gömülür; model belge üzerinden atıfla cevap verir.
  Kabul: örnek bir PDF hakkında soru doğru cevaplanıyor.
  Doğrulama: 18.07.2026 — küçük TXT'ten "17 gemi + Ayşe Karaca" birebir doğru ve
  [BELGE: kucuk.txt] atıflı döndü; PDF'ten gizli kod atıfla döndü. Belge bağlamında
  num_ctx otomatik 16384'e çıkıyor; belgesiz sohbet etkilenmiyor (duman testi HAZIR).
- [x] **2.3 Kalıcı bilgi tabanı (vektör arama)**: `bge-m3` embedding modeli + hafif yerel
  vektör deposu (sqlite/numpy); büyük belgeler parçalanıp indekslenir, soruya en yakın
  parçalar bağlama alınır. Kabul: 50+ sayfalık belgeden doğru parça bulunup atıfla
  cevaplanıyor. Doğrulama: 18.07.2026 — 72 sayfalık (172k karakter) belge yüklemede
  otomatik 173 parçaya vektörlendi (veri/bilgi.db); 43. sayfaya gömülü gerçek
  ("Zeta Enerji 123,4 milyon TL / Kemal Aydın") soruyla bulundu, model parça
  numarasıyla atıf verdi. FAZ 2 TAMAMLANDI.

### Faz 3 — Rapor Motoru

- [x] **3.1 Excel raporu**: "rapor" niyeti veya 📊 düğmesi → son istihbarat/KAP sonuçları
  openpyxl ile biçimli .xlsx (başlık, tablo, kaynak sayfası) olarak `raporlar/` klasörüne
  yazılır ve arayüzden indirilebilir. Kabul: KAP taraması sonrası tek tıkla açılabilir
  Excel üretiliyor. Doğrulama: 18.07.2026 — KAP "dün" taraması (4 bildirim) sonrası
  /api/rapor ile Moralite_Rapor_20260718_170801.xlsx üretildi; openpyxl doğrulaması:
  2 sayfa (Rapor + Kaynaklar), lacivert başlık, tür "KAP Analizi", 4 kaynak satırı,
  köprülü bağlantılar. İndirme ucu HTTP 200. Arayüzde 📊 Excel Raporu düğmesi;
  istihbarat yoksa açıklayıcı hata dönüyor.
- [x] **3.2 Günlük KAP brifingi**: Tek uçtan (`/api/brifing`) izleme evreninin bugün/dün
  bildirimleri + model özeti + Excel çıktısı. Kabul: tek istekle brifing metni ve dosya
  üretiliyor. Doğrulama: 18.07.2026 — /api/brifing tek istekte: dün+bugün aralığı
  (34 şirket) tarandı, 4 bildirim bulundu, atıflı yönetici özeti üretildi ve Excel
  otomatik yazıldı (rapor olayı + HTTP 200 indirme). Arayüzde 🗞 Günlük KAP Brifingi
  düğmesi; rapor bağlantısı balonda kalıcı (m.raporUrl). gun_araligi artık "dün + bugün"
  birleşik aralığını anlıyor. Belgesiz sohbet duman testi: HAZIR. FAZ 3 TAMAMLANDI.

### Faz 4 — İstihbaratı derinleştirme

- [x] **4.1 Çok turlu web araştırması**: Sentez öncesi model "kaynaklar yeterli mi?"
  değerlendirir; kaynak yoksa veya yetersizse farklı açıdan yeni sorgularla 1 tur daha
  arama yapılır (en fazla 2 tur, toplam 6 kaynak sınırı).
  Kabul: ilk turda kaynak bulunamayan/yetersiz kalan soruda ikinci tur otomatik tetikleniyor.
  Doğrulama: 18.07.2026 — nadir soruda (Kozaklı jeotermal ruhsat devri) ilk turun 4 kaynağı
  yeterlilik kontrolünden geçemedi → [tur2] olayı ile 2 yeni sorgu üretildi → 2 ek kaynak
  (Valilik + Habertürk) eklendi → 6 kaynakla sentez. 0-kaynak dalı: sorgu_uret(onceki=...)
  farklı açıdan sorgular üretiyor (doğrulandı). Arayüzde 🔁 2. tur satırı gösteriliyor.
  Kontrol hattı hata durumunda tek turla devam eder (akışı asla kilitlemez). Duman: HAZIR.
- [!] **4.2 Piyasa geneli KAP akışı** — BLOKE (İNSAN_GEREKLİ): KAP'ın piyasa geneli
  sorgusu yeni Next.js arayüzünde sunucu tarafında gömülü veri DÖNDÜRMÜYOR (şirket
  bazlı sorgular dönüyor, çekirdek onu kullanıyor). Denenen ve başarısız olan yollar
  (18.07.2026): fd/td ve fromdate/todate URL parametreleri (veri bloğu yok),
  /tr/api/memberDisclosureQuery (2× zaman aşımı — emekliye ayrılmış görünüyor),
  RSS uçları (404), RSC başlıklı istek (boş kabuk), tarayıcıda ağ dinleme (sayfa
  panelde tam yüklenmedi), Bigpara/Borsagündem toplayıcıları (404/bağlantı reddi).
  Sonraki adım önerisi: kullanıcıyla birlikte gerçek Chrome'da sorgu sayfasını açıp
  ağ trafiğinden asıl veri ucunu yakalamak (5 dk'lık ortak seans) veya izleme
  evrenini genişletmek. Kalan işlevsellik bundan etkilenmiyor.
- [x] **4.3 Kaynak güvenilirlik etiketi**: Kaynakçada alan adına göre rozet
  (resmî/haber/blog). Kabul: kaynakçada rozetler görünüyor.
  Doğrulama: 18.07.2026 — kap.org.tr/tcmb.gov.tr → RESMÎ (yeşil), haberturk → HABER
  (mavi), bilinmeyen alan ve bozuk URL → DİĞER (gri); balonda üç rozet de tarayıcıda
  görüldü. Kaynakça üretimi tek fonksiyonda (kaynakcaHtml) birleşti — canlı akış ve
  geçmiş yüklemesi aynı yolu kullanıyor. Konsol hatasız.

## 4. Kapsam dışı (bilinçli)

Çok kullanıcılılık/kimlik doğrulama · bulut dağıtımı · ses (STT/TTS) · model eğitimi
(ayrı Colab hattı) · KAP dışı borsa API'leri.

## 5. Teknik çerçeve ve kurallar

- Yığın sabit: Flask + tek dosya HTML/CSS/JS (CDN'siz) + Ollama (`qwen3.5:9b`).
- Her özellik: uygulanır → uçtan uca doğrulanır (API testi + gerekiyorsa arayüz) → PRD'de
  işaretlenir → kısa Türkçe commit niteliğinde not düşülür (git yok; PRD doğrulama satırı).
- Sunucu her backend değişikliğinde yeniden başlatılır; port 8770 sabit.
- Mevcut davranış bozulmaz: her fazdan sonra temel akışlar (sohbet, web modu, KAP modu)
  hızlı duman testinden geçirilir.
- 16 GB RAM tavanı: yeni bağımlılıklar hafif tutulur; embedding modeli ≤1,5 GB.

## 6. Riskler

| Risk | Önlem |
|---|---|
| KAP hız kısıtlaması | Çekirdeğin devre kesici/önbelleği aynen kullanılır |
| RAM baskısı (9B + embedding) | Embedding çağrıları kısa tutulur; gerekirse keep_alive ayarı |
| localStorage sınırı (çoklu sohbet) | Görseller kalıcılığa yazılmaz (mevcut kural) + sohbet başına budama |
| Küçük model atıf disiplini | Sistem talimatlarında örnekli biçim zorlaması |
