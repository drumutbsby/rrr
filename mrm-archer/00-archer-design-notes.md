# MRM – Archer Çözüm Mimarisi Tasarım Notları (çalışma dosyası)

## Mevcut Archer envanterinden yeniden kullanılacaklar (arayüz turundan)
- Organizasyon Yönetimi → İş Hiyerarşisi (GMY / Daire Başkanlığı / Bölüm Müdürlüğü) → **model sahibi org birimi**
- İş Altyapısı: IT Hizmetleri, Bankacılık Süreçleri, İş Süreçleri, Kontaklar, **Tedarikçi**, Tesisler
- BT Altyapısı: **Uygulamalar**, **Donanımlar**
- Bilgi Güvenliği: **Bilgi Varlıkları Envanteri** → model girdi verisi / veri varlığı bağlantısı
- BT/Bankacılık Risk: **Risk Hiyerarşisi**, **Risk** → toplulaştırılmış model riski
- **Kontroller** (Kontrol Yönetimi)
- **Metrikler / Metrik Sonuçları** → sürekli izleme (KPI/KRI)
- **Bulgular + Aksiyon Planları** (Bulgu Yönetimi, paylaşımlı) → validasyon bulguları + remediation
- **Görev Yönetimi** → görevler
- Uyumluluk: **Yasal Mevzuatlar** → düzenleme eşleme; **Politikalar ve Standartlar** → model politikası
- Denetlenen Görüşleri, PPM Entegrasyonu, Risk Kabul Talepleri (model istisna/kabul için)

## Önerilen yeni Workspace: "Model Riski Yönetimi (MRM)"
### Yeni uygulamalar (applications) ve anketler (questionnaires)
1. **Model Envanteri** (ana kayıt / master) — bankanın tüm modelleri ve algoritmaları
2. **Model Kritiklik / Materyalite Değerlendirmesi** (questionnaire, skorlu → tier üretir)
3. **Model Validasyonu** (validasyon çalışmaları / engagement kaydı)
4. **Model İzleme – Performans Metrikleri** (Metrikler/Metrik Sonuçları'nı yeniden kullan; MRM'e özel metrik seti)
5. **Model Değişiklik Yönetimi** (change/version kayıtları)
6. **AI/ML Ek Değerlendirmesi** (questionnaire — açıklanabilirlik, yanlılık, drift, retraining, insan gözetimi)
7. **Model Onayları / Model Risk Komitesi Kararları** (approval kayıtları) — opsiyonel, workflow ile Envanter'e gömülebilir
8. **Model Bulguları** → mevcut **Bulgular** uygulamasında "Bulgu Kaynağı = Model Validasyonu" değeri ekleyerek yeniden kullan (yeni uygulama açma)

### İlişki haritası (cross-references / leveraged fields)
- Model Envanteri → Organizasyon (sahip birim), Tedarikçi (satıcı model), Uygulamalar/Donanımlar/IT Hizmetleri (barındıran sistem), Bilgi Varlıkları (girdi verisi), Risk/Risk Hiyerarşisi (ilişkili risk), Kontroller, Yasal Mevzuatlar (ilgili düzenleme), Politikalar
- Model Envanteri ↔ Model Envanteri (self-reference: upstream/downstream model bağımlılıkları — feeder/consumer)
- Model Validasyonu → Model Envanteri (1..N), Bulgular (üretilen bulgular), Görev Yönetimi
- Model İzleme (Metrik Sonuçları) → Model Envanteri, eşik aşımı → Bulgu
- Model Değişiklik → Model Envanteri, tetiklediği revalidasyon → Model Validasyonu

## Model Yaşam Döngüsü (state machine — Values List)
Taslak/Tanımlama → Geliştirme → Bağımsız Validasyonda → Onayda (Komite) → Onaylı/Prodüksiyonda → İzlemede → Revalidasyonda → Koşullu Onaylı (mitigant ile) → Askıda/Kısıtlı → Emekli/Devre Dışı

## Archer teknik mekanizmalar
- **Values Lists**: model tipi, model kategorisi, yaşam döngüsü durumu, tier (1/2/3), validasyon sonucu, risk derecesi
- **Advanced Workflow**: validasyon onay akışı (Geliştirici → Bağımsız Validasyon → Model Risk Komitesi → Onay/Ret/Koşullu)
- **Calculated fields**: sonraki validasyon tarihi (= son validasyon + tier'e göre frekans), doğal (inherent) model risk skoru, gecikme bayrağı
- **Data-Driven Events (DDE)**: durum geçişleri, alan görünürlüğü, koşullu zorunluluk
- **Notifications**: yaklaşan/geciken revalidasyon, izleme eşik aşımı, açık bulgu SLA
- **Data Feeds**: MLOps/model geliştirme ortamından envanter/metrik beslemesi (opsiyonel entegrasyon)
- **Access Roles**: 1. hat (model sahibi/geliştirici), 2. hat (MRM/bağımsız validasyon), 3. hat (iç denetim) ayrımı

## Raporlama / Dashboards
- Model envanteri (tier/tip/kategori/durum kırılımı)
- Validasyon takvimi ve gecikmeler
- Açık model bulguları ve remediation durumu
- Toplulaştırılmış model riski ısı haritası
- AI/ML model portföyü ve drift/izleme durumu
- Model Risk Komitesi paneli
