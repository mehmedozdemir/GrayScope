# Changelog

Bu projedeki tüm önemli değişiklikler bu dosyada belgelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) temel alınır ve proje
[Semantic Versioning](https://semver.org/lang/tr/) kurallarına uyar.

## [Unreleased]

### Added
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
