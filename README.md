# GrayScope

> ⚠️ Taslak — Faz 1 (MVP) geliştirme aşamasında.

GrayScope, birden fazla Graylog sunucusuna bağlanıp önceden tanımlanmış sorguları
şehir/müşteri bazında (Türkiye plaka kodu = `NetworkId`) **parametrik** olarak
çalıştıran ve sonuçları sıralanabilir bir tabloda gösteren bir PySide6 masaüstü
uygulamasıdır.

Birincil senaryo: operasyon/destek ekibinin bir sorgu şablonunu (örn. "Şehir bazlı
200 dışı HTTP yanıtları") seçip, hangi şehir/müşteri için çalıştıracağını seçerek
sonuçları anında görmesi.

## Gereksinimler

- Python 3.11+
- `requirements.txt` içindeki bağımlılıklar (PySide6, httpx, cryptography, pytest)

## Hızlı Başlangıç

```bash
# Sanal ortam
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Bağımlılıklar
pip install -r requirements.txt

# Uygulamayı çalıştır (UI Faz 1'de eklenecek)
python -m app.main

# Testler
pytest
```

İlk çalıştırmada:
- SQLite veritabanı `data/grayscope.db` altında otomatik oluşturulur (repoya girmez).
- 81 il plaka kodu `Customer` tablosuna seed edilir.
- Fernet şifreleme anahtarı `~/.grayscope/secret.key` altında oluşturulur (repoya girmez).

## Yapılandırma

Çevre değişkenleri opsiyoneldir, varsayılanlar çoğu durumda yeterlidir. Tam liste için
[.env.example](.env.example) dosyasına bakın.

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `GRAYSCOPE_KEY_DIR` | Fernet anahtar dosyasının (`secret.key`) bulunduğu dizin | `~/.grayscope` |
| `GRAYSCOPE_DB_PATH` | SQLite veritabanı dosyasının yolu | `<proje>/data/grayscope.db` |

## Mimari

Katmanlı mimari (detay: [CLAUDE.md](CLAUDE.md) §5):

```
ui/            → Görünüm + kullanıcı etkileşimi (iş kuralı yok)
services/      → İş kuralları (placeholder enjeksiyonu, cache, bağlantı testi)
data/          → SQLite CRUD (repository pattern, tablo başına bir repository)
integrations/  → Graylog REST API istemcisi
core/          → Şifreleme, ayarlar, exception'lar
```

`ui/` katmanı asla doğrudan `data/` veya `integrations/`'i çağırmaz — her zaman
`services/` üzerinden geçer.

Güvenlik kuralları (token şifreleme, anahtar yönetimi, query whitelist) için
[CLAUDE.md](CLAUDE.md) §6'ya bakın.

## Katkı

- Branch stratejisi: `feature/*`, `fix/*`, `docs/*` — `main`'e doğrudan commit yok.
- Commit formatı: Conventional Commits (`type(scope): açıklama`).
- `feat`/`fix` değişiklikleri [CHANGELOG.md](CHANGELOG.md) günceller.
- Detaylı kurallar: [CLAUDE.md](CLAUDE.md).

## Dokümantasyon

- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) — fonksiyonel kapsam, veri modeli, akışlar
- [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) — ekran/bileşen tasarım kararları
