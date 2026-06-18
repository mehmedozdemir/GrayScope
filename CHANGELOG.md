# Changelog

Bu projedeki tüm önemli değişiklikler bu dosyada belgelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) temel alınır ve proje
[Semantic Versioning](https://semver.org/lang/tr/) kurallarına uyar.

## [Unreleased]

### Added
- Kapsamlı UI overhaul: sol sidebar kaldırıldı; sorgular en solda **ağaç yapısında**
  (iç içe klasörler + klasör altında sorgular) listelenir. Klasör işlemleri sağ-tık
  menüsü (Yeni Klasör / Alt Klasör / Yeniden Adlandır / Sil), sorgu formunda **Klasör**
  seçici. Veri modeli: `QueryFolder` tablosu + `Query.FolderId` (otomatik migrasyon).
- **Ayarlar ve Tanımlamalar** modalı (sol-alt ⚙) — Graylog Profilleri ve Müşteriler
  sekmeli olarak buradan yönetilir.
- **Açık tema** eklendi; sol-alt ikonla anlık tema değişimi, tercih kalıcı (QSettings).
- Parametre şeridi, sorgu ağacı ve sorgu metni alanından koyu dolgu kaldırıldı.
- Proje iskeleti: klasör yapısı, `requirements.txt`, `.gitignore`, `.env.example`,
  `README.md` taslağı, `CHANGELOG.md`.
- SQLite şema ve repository katmanı: `GraylogProfile`, `Customer`, `Query`, `QueryStream`.
- `core/encryption.py`: Fernet tabanlı token şifreleme/çözme ve anahtar dosyası yönetimi.
- `data/seed/turkish_cities.py`: 81 il plaka kodu + isim seed verisi.
- Repository katmanı için happy-path pytest testleri.
- UI tasarım sistemi: `ui/theme.py` (design token'lar) + `ui/stylesheets.py` (global QSS, dark theme).
- Çekirdek UI bileşenleri: buton varyantları, arama/etiketli alan input'ları, tablo paneli
  (empty state'li), sidebar navigasyon, onay dialog'u, toast/badge/empty-state feedback.
- Uygulama kabuğu: `ui/main_window.py` (sidebar + sayfa stack).
- Müşteriler ekranı: arama + CRUD (ekle/düzenle/sil), aktif/pasif rozet.
- Graylog REST istemcisi (`integrations/graylog/`) + `connection_test_service`.
- Graylog Profilleri ekranı: CRUD + asenkron "Bağlantıyı Test Et" (token maskeli/şifreli).
- `GraylogClient` HTTP hata eşleme testleri (httpx MockTransport).
- Sorgular ekranı: master-detail (QSplitter) sorgu listesi + detay, parametrik sorgularda
  arama destekli müşteri seçici, "Çalıştır" (müşteri seçilmeden disabled), sonuç grid'i
  (client-side `QSortFilterProxyModel` sıralama), loading/empty/error durumları.
- Yeni/Düzenle Sorgu dialog'u: profil, müşteri parametresi, monospace sorgu metni,
  profile göre async stream seçimi (yenile + hata durumu), 3 sekmeli tarih aralığı,
  chip tabanlı alan girişi, varsayılan sıralama, sonuç limiti.
- `query_execution_service` ({Plaka} enjeksiyonu + tarih aralığı) ve
  `stream_catalog_service` (profil bazlı cache); `GraylogClient.execute_search`
  (POST /search/messages, CSV parse).
- `ChipInput` bileşeni; sorgu çalıştırma ve CSV parse için offline testler.
- Sorgular ekranı çalıştırma satırı: grid üstünde düzenlenebilir **sorgu metni** alanı
  (seçili sorgunun değeriyle dolar, kaydetmeden geçici düzenleyip yeniden çalıştırılabilir)
  ve **kayıt sayısı** alanı (seçili sorgunun değeriyle dolar; **0 = tüm kayıtlar**).
  Müşteri seçici kendi satırına alındı. Parametreler + çalıştırma kontrolleri tek
  bir kart panel içinde gruplandı; parametre alanı ile sorgu/çalıştır satırı ince bir
  ayraçla ayrıldı, parametre alanı yalnızca parametrik sorgularda görünür.
- Sorgular ekranı: sonuç grid'inin altında sabit **full-text arama** kutusu — yazdıkça
  içeriğinde aranan değeri geçen hücreler vurgu rengiyle (amber) işaretlenir
  (filtrelemez, vurgular). `*` ve `?` joker karakterleri desteklenir. Vurgu, QSS'i
  baypas etmek için özel bir delegate ile çizilir.
