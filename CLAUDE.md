# CLAUDE.md — GrayScope

Bu dosya, Claude Code'un bu proje üzerinde çalışırken uyması gereken kuralları tanımlar.
Bu dosya, global `engineering-standards` ve `pyside6-ui-ux` skill'lerini **override etmez**,
onların üzerine proje-özel kuralları ekler. Çakışma olursa bu dosyadaki kural önceliklidir.

---

## 1. Zorunlu Okuma Sırası (Kod Yazmaya Başlamadan Önce)

1. `/mnt/skills/user/engineering-standards/SKILL.md` — her proje için temel kurallar
2. `/mnt/skills/user/pyside6-ui-ux/SKILL.md` — her UI ekranı/bileşeni için zorunlu
3. `docs/PROJECT_PLAN.md` — fonksiyonel kapsam, veri modeli, ekran akışları, kabul kriterleri
4. `docs/DESIGN_SYSTEM.md` — bu projeye özel ekran/bileşen tasarım kararları
5. Bu dosyanın kalanı

Bu sıralama her yeni görev/oturum başında geçerlidir — "zaten okudum" diye atlanmaz.

---

## 2. Proje Özeti

GrayScope, birden fazla Graylog sunucusuna bağlanabilen, sorguları **parametrik** olarak
(şehir/plaka koduna göre `NetworkId` enjeksiyonu ile) tanımlayıp çalıştırabilen ve sonuçları
sıralanabilir bir tablo üzerinde gösteren bir PySide6 masaüstü uygulamasıdır.

Birincil kullanıcı senaryosu: Operasyon/destek ekibinin önceden tanımlanmış bir sorgu şablonunu
(örn. "Şehir bazlı 200 dışı HTTP yanıtları") seçip, hangi şehir/müşteri için çalıştırmak istediğini
seçerek sonuçları anında görmesi.

---

## 3. Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.11+ |
| UI | PySide6 |
| Yerel veritabanı | SQLite (`data/grayscope.db`, runtime'da oluşturulur, repoya girmez) |
| HTTP istemcisi | httpx |
| Şifreleme | `cryptography` (Fernet) — Graylog token'ları için |
| Test | pytest |
| Paket yönetimi | `requirements.txt` (sabit versiyonlar, lockfile mantığıyla) |

Yeni bağımlılık eklemeden önce mevcut kütüphanelerle çözülüp çözülemeyeceği değerlendirilmeli
(engineering-standards: "minimal permissions" kuralı).

---

## 4. Proje Yapısı

```
grayscope/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py              # Uygulama genel ayarları, sabitler
│   │   ├── encryption.py          # Fernet şifreleme/şifre çözme yardımcıları
│   │   └── exceptions.py          # Uygulama-özel exception sınıfları
│   ├── data/
│   │   ├── database.py            # SQLite bağlantısı, şema oluşturma/migrasyon
│   │   ├── models/
│   │   │   ├── graylog_profile.py
│   │   │   ├── customer.py
│   │   │   ├── query.py
│   │   │   └── query_stream.py
│   │   ├── repositories/
│   │   │   ├── graylog_profile_repository.py
│   │   │   ├── customer_repository.py
│   │   │   ├── query_repository.py
│   │   │   └── query_stream_repository.py
│   │   └── seed/
│   │       └── turkish_cities.py  # 81 il plaka kodu seed verisi
│   ├── integrations/
│   │   └── graylog/
│   │       ├── client.py          # httpx tabanlı Graylog REST istemcisi
│   │       ├── schemas.py         # request/response veri sınıfları (dataclass)
│   │       └── exceptions.py      # GraylogConnectionError, GraylogAuthError, vb.
│   ├── services/
│   │   ├── query_execution_service.py   # {Plaka} enjeksiyonu + Graylog çağrısı orkestrasyonu
│   │   ├── stream_catalog_service.py    # profile göre stream listesi + cache
│   │   └── connection_test_service.py   # "Bağlantıyı Test Et" iş mantığı
│   └── ui/
│       ├── theme.py
│       ├── stylesheets.py
│       ├── main_window.py
│       ├── components/
│       │   ├── buttons.py
│       │   ├── inputs.py
│       │   ├── tables.py
│       │   ├── navigation.py
│       │   ├── dialogs.py
│       │   └── feedback.py
│       └── pages/
│           ├── queries_page.py
│           ├── query_form_dialog.py
│           ├── customers_page.py
│           └── graylog_profiles_page.py
├── tests/
│   └── (app/ ile aynı yapı, dosya başına 1 test modülü)
├── data/                           # .gitignore'da, sadece runtime SQLite dosyası
├── docs/
│   ├── PROJECT_PLAN.md
│   └── DESIGN_SYSTEM.md
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
├── requirements.txt
└── CLAUDE.md
```

---

## 5. Mimari Katmanlar ve Sorumluluklar

```
ui/            → Sadece görünüm + kullanıcı etkileşimi. İş kuralı YOK.
services/      → İş kuralları: placeholder enjeksiyonu, zaman aralığı hesaplama,
                 stream cache yönetimi, bağlantı testi orkestrasyonu.
data/          → SQLite CRUD. Repository pattern — her tablo için bir repository.
integrations/  → Sadece Graylog REST API ile konuşur. Hiçbir iş kuralı barındırmaz,
                 sadece HTTP isteği kurar/gönderir/parse eder.
```

**Kural:** `ui/` katmanı doğrudan `integrations/graylog` veya `data/repositories`'i
çağırmaz — her zaman `services/` üzerinden geçer. Bu, UI'ı test edilebilir ve
Graylog API değişikliklerinden izole tutar.

---

## 6. Güvenlik Kuralları (Proje Özel)

- Graylog token'ları **hiçbir zaman düz metin saklanmaz**. `core/encryption.py` üzerinden
  Fernet ile şifrelenip `GraylogProfile.TokenEncrypted` alanına yazılır.
- Fernet şifreleme anahtarı koda **gömülmez**. İşletim sisteminin kullanıcı profili altında
  ayrı bir anahtar dosyasında saklanır (örn. `~/.grayscope/secret.key`, dosya izinleri
  kullanıcıya özel — 0600). Bu dosya `.gitignore`'da olmalı, repoya asla girmemeli.
- Token, hiçbir log satırında, exception mesajında veya konsol çıktısında düz metin
  görünmemeli — hata mesajlarında token maskelenir (`****1234` gibi son 4 karakter).
- Sorgu şablonundaki `{Plaka}` placeholder'ı dışında kullanıcıdan serbest metin Graylog
  query string'ine doğrudan enjekte edilmeden önce temel bir whitelist kontrolünden
  geçirilir (alfanumerik + Lucene operatörleri ile sınırlı; ham SQL/komut enjeksiyonu
  riski olmasa da savunma amaçlı).
- `.env.example` içinde gerçek değer olmaz, sadece değişken adları + açıklama.

---

## 7. Kodlama Standartları

- `engineering-standards` skill'indeki tüm kurallar geçerli (commit formatı, branch
  stratejisi, semantic versioning, naming conventions).
- Sınıf/metot/alan isimleri **İngilizce** (örn. `NetworkId`, `IsActive`, `QueryTemplate`).
- Kullanıcıya gösterilen tüm UI metinleri **Türkçe**.
- Her repository sınıfı tek bir tablo ile ilgilenir, çapraz sorgu gerekiyorsa bu mantık
  `services/` katmanına taşınır.
- Graylog API çağrıları her zaman timeout ile yapılır (önerilen: 10 saniye), timeout
  durumunda kullanıcıya anlaşılır bir hata gösterilir.

---

## 8. UI Geliştirme Kuralları

`pyside6-ui-ux` skill'i bu proje için **istisnasız** geçerlidir. Ek olarak:

- Tüm ekranlar `docs/DESIGN_SYSTEM.md`'de tanımlanan layout kararlarına uyar.
- Sol navigasyon sidebar: Sorgular (varsayılan açılış sayfası) → Müşteriler →
  Graylog Profilleri.
- Sorgular ekranı, `pyside6-ui-ux`'teki "Dashboard Architecture" master-detail
  pattern'ini kullanır (QSplitter: sol liste / sağ içerik).
- Her async işlem (Graylog API çağrısı, bağlantı testi) için loading state zorunlu.

---

## 9. "Definition of Done" — Her Özellik İçin

- [ ] `PROJECT_PLAN.md`'deki ilgili FR (Functional Requirement) kabul kriterleri karşılanıyor
- [ ] `pyside6-ui-ux` "Checklist Before Delivering Any UI" tamamlandı
- [ ] İlgili hata senaryoları (bağlantı hatası, geçersiz token, boş sonuç, geçersiz
      stream ID) test edildi
- [ ] Token hiçbir çıktıda düz metin görünmüyor
- [ ] Yeni/değişen davranış için en az 1 happy-path + 1 edge-case testi yazıldı
- [ ] CHANGELOG.md güncellendi (feat/fix ise)

---

## 10. Kapsam Dışı — Faz 2 (Şimdilik Yapılmayacak)

Bu öğeler `PROJECT_PLAN.md`'de backlog olarak kayıtlı, **Faz 1'de implemente edilmez**.
Kod içinde bunlara yer açan soyutlama yapılabilir ama UI'da görünür/aktif olmaz:

- CSV/Excel export
- Sorgu çalıştırma geçmişi (son çalıştırma zamanı, sonuç sayısı kaydı)
- Sorgu kategorileme/klasörleme
- Çalıştırma anında tarih aralığını geçici override etme

---

## 11. Sorulması Gereken Durumlar

Aşağıdaki durumlarda Claude Code kod yazmadan önce kullanıcıya sormalı, varsayım
yapıp ilerlememeli:

- Graylog sunucu sürümleri arasında API farkı şüphesi varsa (bkz. PROJECT_PLAN.md §3)
- Bir ekranın layout'u DESIGN_SYSTEM.md'de tanımlı değilse
- Veri modelinde PROJECT_PLAN.md'de yer almayan yeni bir alan/tablo gerekiyorsa
