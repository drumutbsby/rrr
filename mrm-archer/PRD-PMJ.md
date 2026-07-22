# PRD — Prometeia Model Journey (PMJ) Simülasyonu

**Amaç:** Mevcut "MRM Konsolu" simülasyonunu, Prometeia Model Journey (PMJ) ürününün (Halkbank kurulumu) görünümü, taksonomisi ve iş akışlarıyla birebir örtüşen bir demoya dönüştürmek. Mevcut zengin MRM işlevselliği (modeller, validasyon, izleme, tiering, bulgular, denetim) veri/hesap katmanı olarak korunur; UI ve süreç yapısı PMJ'ye hizalanır.

**Build hedefi:** `mrm-archer/pmj/index.html` (kaynak) → deploy `docs/pmj/index.html` → https://drumutbsby.github.io/rrr/pmj/ . Mevcut `/mrm` stabil kalır; PMJ tamamlanınca opsiyonel olarak `/mrm` PMJ'ye yönlendirilebilir.

**Kalite kuralı:** Her faz Chromium (Playwright) ile doğrulanır (konsol hatası = 0), ayrı commit'lenir, `/pmj` yeniden deploy edilir. Her faz sonunda uygulama çalışır durumda kalır.

---

## Marka & Genel
- **Prometeia teması:** lacivert üst bar (`#12235c`), Prometeia yeşili aksan (`#3aa935` / `#2e9e5b`), beyaz içerik; yeşil yaprak logo (SVG/emoji placeholder), "prometeia" kelime markası.
- **Bağlam:** Kullanıcı "Gizem Atasoy · mmm-sso-user · Turkish Branch"; Halkbank modelleri.
- Açık/koyu tema korunur (PMJ açık ağırlıklı).

## Roller (kullanıcı menüsü)
APIUser · Model Developer · Internal Audit Officer · Model User · Model Risk Manager · Model Owner · Settings · About. Rol seçimi görünüm/yetki kısıtı sürücüsüdür (3 savunma hattı eşlemesi korunur).

## Üst navigasyon (ana modüller)
`Registry · Map · Issues · Documentation · Dashboards · Activities` + sağda kullanıcı/rol menüsü. Ayrı **Admin portal** (Home · Register Configuration · Reporting · Settings · Audit Tools).

---

## Durum: ✅ P1–P15 TAMAM (deploy: https://drumutbsby.github.io/rrr/pmj/)

Tüm fazlar uygulandı, Chromium ile doğrulandı (21 kullanıcı rotası + 7 model bölümü × 3 model + 5 admin rotası = 0 konsol hatası) ve `docs/pmj/` altında GitHub Pages'e deploy edildi. Ana sayfa (Moralite) ve `/mrm` korunur.

## FAZLAR (loop bu sırayı izler)

### P1 — PMJ Kabuğu & Marka & SSO ✅ kabul: üst nav + Prometeia marka + rol menüsü + SSO açılış (Administrator/User Portal) çalışır; mevcut view'lar modüllere yönlenir; 0 hata.
- SSO açılış ekranı ("Welcome to Prometeia's Enterprise Management Solution" → Administrator Portal / User Portal / Back).
- Lacivert üst nav bar + 6 modül sekmesi + kullanıcı/rol dropdown (roller listesi).
- Router'ı üst-nav modüllerine bağla; mevcut ekranları geçici olarak ilgili modüle map et.

### ✅ P2 — Registry (Model Envanteri, PMJ grid)
- Sol kategori ağacı (Cat_test_gp / Archived), "+ New Item".
- Grid sütunları: **Code · Description · Version · Lifecycle phase · Model Adı · Model Güncelleme · Statü · Model Tipi · Modeli Geliştiren · Demand di riferimento · ID Progetto · Area Model**.
- Taksonomi: Lifecycle phase (İş İhtiyaç ve Gereksinim → Model Geliştirme → İmplementasyon → Yayımlaştırma ve Kullanım); Statü (Talep edildi / Geliştirmede / Üretimde); Model Tipi (İLERİ ANALİTİK MODEL / BASİT MODEL).
- Sütuna göre gruplama, sayfalama, arama. Mevcut modelleri PMJ satırlarına eşle; eksik PMJ alanlarını veri modeline ekle (code, description, lifecyclePhase, statu, modelTipi, department, area, demand, projeId).

### ✅ P3 — Model Detay Kabuğu & Versiyon
- Breadcrumb: Registry > Kategori > Model > Vx - tarih; **versiyon seçici** + **New Version**.
- Sol menü: Lifecycle · Map · History · DETAILS(faz sayfaları) · Issues · Documentation.
- "Calculate fields during Save" anahtarı; kaydet/dışa aktar ikonları.

### ✅ P4 — Model Lifecycle (10 faz)
- Dikey stepper; her faz: Step n, Completed/In Progress, **Total Fields / Mandatory Fields (x/x)**, Close Date, halka %; faz kontrolü: **Reopen Phase** (tamamlanmış), **Skip Phase / Close Phase** (devam eden).
- Üstte versiyon ilerleme % (tamamlanan mandatory oranından hesaplanır).
- 10 faz: 1 İş İhtiyaç ve Gereksinim Analizi · 2 Model Tanımı · 3 Model Envanteri · 4 Model Geliştirme · 5 İmplementasyon Öncesi Validasyon · 6 İçsel/Dışsal Onay · 7 İmplementasyon ve Entegrasyon · 8 İmplementasyon Sonrası Validasyon · 9 Model Risk Onay/İzleme · 10 Yaygınlaştırma ve Bakım.

### ✅ P5 — Faz Formu Motoru (generic) & S.00, S.01, S.02
- Alan deseni: **R_Sxx_n** (dropdown/richtext/numeric/date, `*`=zorunlu) · **Note_Sxx_n** (richtext) · **Detaylar/Belgesel Referanslar** (dosya) · faz-içi sekmeler.
- S.00 Model Bilgi Sayfası (Geliştirme İhtiyacı / Geliştirme ve Üretim Zamanlaması): R_S00_1..6.
- S.01 Model Türünün Tanımlanması.
- S.02 Envanter (Tüm Fazlar): sekmeler Model Özellikleri / Dokümantasyon / Kontrol-Denetim / Yönetişim; alanlar: Model Adı*, Versiyon*, Model Güncelleme Statüsü, Statü*, Hedef Segment*, İmplementasyon Planlanan Tarih, Gereksinim Analizi Bitiş, Sonraki Faza Geçiş, Model Yaşam Döngüsü*, Model No*, Modeli Geliştiren Kaynak, Model Hedef Değişken Tanımı*, Modeli Geliştiren Departman*, Uygulama Kapsamı*.
- Form doldurma → faz mandatory tamamlanma %'sini besler (Lifecycle ile bağ).

### ✅ P6 — Tiering (Sınıf 1–4, 3 boyutlu skorlu)
- **S.03.A Kapsamlılık Derecesi** (materyalite), **S.03.B Karmaşıklık & Belirsizlik** (5 alt sekme: Girdi ve Veri / Modeller ve Metodolojiler / Süreçler-Yönetişim / BT Sistemleri / Sonuçlar), **S.03.C İş Etkisi Derecesi**.
- Her soru: R_S03x_n (nitel dropdown) → **S_S03x_n (0–1 skor)**; KVKK/BDDK referanslı sorular.
- Üç boyut skorları toplulaştırılır → **Sınıf 1–4** (küp; Sınıf 1 kırmızı=en yüksek, Sınıf 4 yeşil). Mevcut scoreCrit mantığı 3-boyut/0-1'e uyarlanır.

### ✅ P7 — S.04.A/B/C, Sonuçlar & Performans Metrikleri
- S.04.A Model Riskini Azaltma (5.Faz), S.04.B 3.–4. Seviye Bulguları (9.Faz), S.04.C Validasyon Bulguları (5,8.Faz: R_S04C_1 düzenleyici bulgu var mı, R_S04C_2 adet + belge referansı).
- **Sonuçlar** sekmesi → **Performans Metrikleri** grid: Metric Date · Metric Name · Train Score · Test Score · OOT; Add Row · Export. Mevcut izleme metriklerini besle. Support Fields.

### ✅ P8 — Issues Modülü
- Sol filtreler: Open · Reported Open · Assigned Open · Recently Closed · Recent · Favorite · Generic Open/Closed; "+ New Issue".
- Issue detay: Title · Description(richtext) · Attachment · Comments; sağ **Details** paneli: Creation/Last Update · Issue Connection · Related Items(model-vX) · Reporter · Assignee · **Status** · **Priority**(Major/…) · **Resolution**(Done) · **Type**(Task) · **Due Date**; History sekmesi. Mevcut bulguları Issues'a eşle.

### ✅ P9 — Documentation Modülü
- Doküman havuzu (favoriler/son), model/faz bazlı belge referansları, versiyonlama görünümü. Mevcut Gereklilik/Regülasyon içerikleri de burada referans olarak.

### ✅ P10 — Dashboards Modülü
- Mevcut Genel Bakış · Risk Panosu & Board · İştah · izleme panolarını PMJ Dashboards altında topla; grafik/gösterge.

### ✅ P11 — Activities Modülü
- İş akışı/görev/aktivite akışı; bildirim & eskalasyon; yaşam döngüsü geçiş aktiviteleri; denetim izi. Mevcut Bildirim/Yaşam Döngüsü/Denetim.

### ✅ P12 — Map Modülü
- Model ilişki/bağımlılık haritası (mevcut ağ grafiği), etki analizi; item detay/lifecycle/issues/relation.

### ✅ P13 — Admin Portal
- Home · Register Configuration · Reporting · Settings · Audit Tools.
- **Settings > System Configuration:** Attachment Max Size (2GB), Document Area max favorites (50), Max recent documents (50), Issues max favorites (50), Max recent issues (50), Admitted attachment file types (doc/docx/…); **Downloads** (Item details+Lifecycle+Issues+Relation map → Create / Open Queue).

### ✅ P14 — Roller & Yetki
- Rol menüsü işlevsel; rol bazlı görünüm/yetki (Model Owner/Developer/User/Risk Manager/Internal Audit/APIUser); validasyon bağımsızlığı ve iç denetim salt-okur korunur.

### ✅ P15 — Cila & Deploy & (ops.) /mrm repoint
- Konsept çerçeveler (4 element sütunu, 3 modül, MRM 5 prensip, model tanımı karar ağacı) About/Documentation'a; genel cila; tam süpürme testi; `/pmj` final; istenirse `/mrm` → PMJ.

---

## Veri modeli eklemeleri (PMJ alanları)
`model.code, model.description, model.lifecyclePhase, model.statu, model.modelTipi (İLERİ ANALİTİK/BASİT), model.department, model.area, model.demand, model.projeId, model.versions[], model.phases{ id: {completed, totalFields, mandatoryFilled, mandatoryTotal, closeDate, fields{} } }, model.tieringSinif (1-4), model.s03scores{A,B,C}, issues[], documents[]` — mevcut alanlar (sinif, metricProfile, crit, metrics, links…) korunur.

## Taksonomi sabitleri
- Lifecycle phase: İş İhtiyaç ve Gereksinim Analizi · Model Tanımı · Model Envanteri · Model Geliştirme · İmplementasyon Öncesi Validasyon · İçsel/Dışsal Onay · İmplementasyon ve Entegrasyon · İmplementasyon Sonrası Validasyon · Model Risk Onay/İzleme · Yaygınlaştırma ve Bakım.
- Statü: Talep edildi · Geliştirmede · Üretimde (+ mevcut durumlar eşlenir).
- Model Tipi: İLERİ ANALİTİK MODEL · BASİT MODEL.
- Sınıf (Tier): Sınıf 1 (kırmızı) · Sınıf 2 (turuncu) · Sınıf 3 (sarı) · Sınıf 4 (yeşil).
- Issue: Status(Open/Assigned/Resolved/Closed) · Priority(Blocker/Major/Minor) · Resolution(Done/…) · Type(Task/…).
