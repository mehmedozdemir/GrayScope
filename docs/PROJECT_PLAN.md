# PROJECT_PLAN.md — GrayScope

## 1. Amaç

Operasyon ekibinin, birden fazla Graylog sunucusunda önceden tanımlanmış sorguları
şehir/müşteri bazında (Türkiye plaka kodu = `NetworkId`) parametrik olarak çalıştırıp
sonuçları tek bir masaüstü arayüzde, sıralanabilir bir tabloda incelemesini sağlamak.

## 2. Kapsam

### Faz 1 (MVP — bu doküman kapsamı)
- Çoklu Graylog sunucu profili yönetimi
- Müşteri/plaka referans tablosu (81 il + özel kayıt)
- Parametrik sorgu tanımlama ve CRUD
- Çoklu stream seçimi
- 3 tip tarih aralığı (Relative / Absolute / Keyword)
- Sorgu çalıştırma + sonuç grid'i + client-side sıralama

### Faz 2 (Backlog — kapsam dışı, sadece referans amaçlı)
- CSV/Excel export
- Sorgu çalıştırma geçmişi
- Sorgu kategorileme/klasörleme
- Çalıştırma anında tarih aralığı override

---

## 3. Graylog Entegrasyonu

### 3.1 Hedef Sürüm
Geliştirme Graylog **5.1.2** baz alınarak yapılır. Bu sürümde "Search Scripting API"
(`/api/search/messages`, `/api/search/aggregate`) etkindir. Her yeni profil eklenirken
sürüm farkı riskine karşı bağlantı testi sırasında bu endpoint'in erişilebilirliğini
de kontrol etmek faydalı olur (bkz. §6.3).

### 3.2 Kullanılan Endpoint'ler

| Amaç | Method | Endpoint |
|---|---|---|
| Mesaj/sorgu sonucu çekme | POST | `/api/search/messages` |
| Bağlantıyı test etme | GET | `/api/system` (basit, yetki gerektirmeyen bilgi endpoint'i) |
| Stream listesi çekme | GET | `/api/streams` |

### 3.3 Kimlik Doğrulama
- Basic Auth: `(token, "token")` — Graylog'un token-tabanlı kimlik doğrulama deseni.
- Her istekte zorunlu header'lar: `Accept: application/json`, `X-Requested-By: GrayScope`.

### 3.4 Sorgu Şablonu / Parametre Enjeksiyonu

Bir sorgu, `UsesCustomerParameter = true` ise şablonunda `{Plaka}` placeholder'ı
barındırabilir:

```
Şablon:  NetworkId:{Plaka} AND NOT StatusCode:200
Seçim:   İstanbul (NetworkId=34)
Sonuç:   NetworkId:34 AND NOT StatusCode:200
```

`UsesCustomerParameter = false` olan sorgular placeholder içermez, doğrudan
`QueryTemplate` metniyle çalıştırılır (örn. genel/sistem geneli bir hata sorgusu).

### 3.5 Tarih Aralığı Tipleri

| Tip | Saklanan Alanlar | Davranış |
|---|---|---|
| Relative | `TimeRangeRangeSeconds` (int) | Her çalıştırmada "şu an - N saniye → şu an" olarak yeniden hesaplanır |
| Absolute | `TimeRangeFrom`, `TimeRangeTo` (datetime) | Sabit tarihsel pencere, her çalıştırmada aynı kalır |
| Keyword | `TimeRangeKeyword` (string, örn. "yesterday") | Graylog tarafında her çalıştırmada güncel saate göre yeniden yorumlanır |

**Önemli varsayım:** Relative ve Keyword tipleri "şimdiye göre" tanımlandığı için
saklanan değer bir zaman damgası değil, bir **kural**dır (örn. "son 3600 saniye").
Absolute tip ise gerçekten sabit bir tarihsel pencereyi temsil eder — incident
analizi gibi durumlar için kasıtlı olarak değişmemelidir.

### 3.6 Stream Seçimi
- Stream listesi, seçilen `GraylogProfileId`'ye göre `/api/streams`'den çekilir ve
  isim bazlı gösterilir; arka planda ObjectId (hex string) saklanır.
- Bir sorgu birden fazla stream'e bağlanabilir (çoklu seçim onaylandı).
- Stream listesi `stream_catalog_service` içinde profil bazlı cache'lenir, kullanıcı
  manuel yenileyebilir (form içinde "Yenile" ikonu).

---

## 4. Veri Modeli

### 4.1 GraylogProfile

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| Id | int (PK) | evet | Otomatik artan |
| Name | string | evet, unique | Kullanıcı tanımlı sunucu adı (örn. "Ana Sunucu") |
| BaseUrl | string | evet | Örn. `https://graylog.sirket.com:9000/api` |
| TokenEncrypted | string | evet | Fernet ile şifrelenmiş token |
| IsDefault | bool | evet (varsayılan: false) | Yeni sorgu formunda ön seçili profil |
| IsActive | bool | evet (varsayılan: true) | Pasifse seçim listelerinde gizlenir |
| CreatedAt | datetime | evet | |
| UpdatedAt | datetime | evet | |

### 4.2 Customer (Müşteriler / Plaka)

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| Id | int (PK) | evet | Otomatik artan, teknik anahtar |
| NetworkId | int | evet, unique | Plaka kodu (1-81 + özel kayıtlar) |
| Name | string | evet | Şehir/müşteri adı |
| IsActive | bool | evet (varsayılan: true) | Pasifse müşteri seçicide gizlenir |
| Description | string | hayır (nullable) | Serbest not |

> `Id` ile `NetworkId` kasıtlı olarak ayrılmıştır — ileride plaka kodu olmayan
> özel/test amaçlı network tanımlarına izin vermek için.

### 4.3 Query (Sorgular)

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| Id | int (PK) | evet | |
| Name | string | evet, unique | Sol panelde gösterilen ad |
| GraylogProfileId | int (FK → GraylogProfile.Id) | evet | Hangi sunucuda çalışacağı |
| UsesCustomerParameter | bool | evet | `{Plaka}` enjeksiyonu aktif mi |
| QueryTemplate | string | evet | Lucene sorgu metni, opsiyonel `{Plaka}` içerir |
| TimeRangeType | enum (Relative/Absolute/Keyword) | evet | |
| TimeRangeRangeSeconds | int | hayır | Sadece Relative için |
| TimeRangeFrom | datetime | hayır | Sadece Absolute için |
| TimeRangeTo | datetime | hayır | Sadece Absolute için |
| TimeRangeKeyword | string | hayır | Sadece Keyword için |
| FieldsJson | string (JSON array) | evet | Grid'de gösterilecek alan adları |
| DefaultSortField | string | hayır | Varsayılan sıralama kolonu |
| DefaultSortOrder | enum (asc/desc) | hayır | |
| ResultSize | int | evet (varsayılan: 150) | Tek seferde çekilecek maksimum kayıt |
| CreatedAt | datetime | evet | |
| UpdatedAt | datetime | evet | |

### 4.4 QueryStream

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| Id | int (PK) | evet | |
| QueryId | int (FK → Query.Id) | evet | |
| StreamId | string | evet | Graylog ObjectId (hex) |
| StreamName | string | evet | Görüntüleme için cache'lenmiş isim |

### 4.5 İlişki Özeti
- `GraylogProfile (1) → (N) Query` — bir profilde birden çok sorgu olabilir
- `Query (1) → (N) QueryStream` — bir sorgu birden çok stream'e bağlanabilir
- `Customer` herhangi bir tabloya FK ile bağlı **değildir** — çalıştırma anında
  seçilip şablona enjekte edilen bağımsız bir referans tablosudur (bkz. ER diyagramı)

---

## 5. Ekranlar ve Akışlar

### 5.1 Genel Navigasyon
Sol sidebar, 3 menü öğesi: **Sorgular** (varsayılan açılış) → **Müşteriler** →
**Graylog Profilleri**.

### 5.2 Graylog Profilleri Ekranı
- Liste: Name, BaseUrl, IsDefault, IsActive kolonları
- Aksiyonlar: Ekle / Düzenle / Sil / **Bağlantıyı Test Et**
- Test Et → `/api/system`'e istek atar, başarı/hata toast gösterir
- Sil işlemi, o profile bağlı sorgu varsa engellenir ve kullanıcıya bilgi verilir

### 5.3 Müşteriler (Plaka) Ekranı
- İlk kurulumda 81 il otomatik seed edilir (`data/seed/turkish_cities.py`)
- Liste: NetworkId, Name, IsActive, Description
- Arama kutusu (isim/plaka koduna göre filtre)
- Ekle / Düzenle / Sil (seed verisi de düzenlenebilir/pasifleştirilebilir, NetworkId
  unique kısıtı her durumda geçerli)

### 5.4 Sorgular Ekranı (Ana İş Ekranı)
- **Sol panel** (master): Arama kutusu + "+ Yeni Sorgu" + sorgu listesi (her satırda
  sorgu adı + bağlı profil adı küçük etiket)
- **Sağ panel** (detail):
  - Hiçbir sorgu seçili değilse: empty state
  - Sorgu seçiliyse: başlık + Düzenle/Sil ikonları
    - `UsesCustomerParameter = true` ise: Müşteri seçici (ComboBox, arama destekli)
      + "Çalıştır" butonu yan yana
    - `UsesCustomerParameter = false` ise: doğrudan "Çalıştır" butonu
  - Çalıştırma sonrası: grid (kolon başlığına tıklayınca artan/azalan sıralama,
    client-side, `QSortFilterProxyModel`)
  - Sonuç yoksa: empty state ("Bu sorgu için kayıt bulunamadı")
  - Hata durumunda: insan-okur hata mesajı (bkz. §6)

### 5.5 Yeni/Düzenle Sorgu Formu
Modal pencere, sırasıyla:
1. Ad
2. Graylog Profili (ComboBox)
3. "Müşteri parametresi kullan" (checkbox) — açıkken şablonda `{Plaka}`
   kullanılabileceğine dair bilgi notu gösterilir
4. Sorgu metni (çok satırlı, monospace font)
5. Stream seçimi (seçili profile göre canlı liste, çoklu seçim, arama destekli)
6. Tarih aralığı (3 sekme: Relative / Absolute / Keyword)
7. Gösterilecek alanlar (etiket/chip tabanlı serbest giriş)
8. Varsayılan sıralama alanı + yön (opsiyonel)
9. Sonuç limiti (sayısal giriş, varsayılan 150)
10. Kaydet / Vazgeç

---

## 6. Hata Senaryoları

| Senaryo | Beklenen Davranış |
|---|---|
| Token geçersiz/süresi dolmuş | "Bu profil için kimlik doğrulama başarısız, lütfen token'ı güncelleyin" + profili düzenleme kısayolu |
| Stream API'den erişilemiyor | "Stream listesi alınamadı, bağlantıyı kontrol edin" toast, form stream alanı boş kalır ama kayıt engellenmez |
| Sorgu çalıştırma timeout | "Graylog sunucusuna ulaşılamadı (zaman aşımı)" |
| Boş sonuç seti | Grid'de tasarlanmış empty state, hata değil bilgi mesajı |
| Geçersiz `{Plaka}` enjeksiyonu (müşteri seçilmeden çalıştırma denemesi) | "Çalıştır" butonu müşteri seçilene kadar disabled |
| Profil silinmeye çalışılıyor ama bağlı sorgu var | Engelle + "Bu profile bağlı N sorgu var, önce onları silin/taşıyın" |

---

## 7. Kabul Kriterleri (Örnek — Önemli Akışlar)

**FR-Query-Run-01:** Parametrik bir sorgu, müşteri seçilmeden "Çalıştır"a
basılamaz (buton disabled, tooltip ile açıklanır).

**FR-Query-Run-02:** Aynı sorgu farklı müşteriler için art arda çalıştırıldığında
her çalıştırma önceki grid'i tamamen temizleyip yeni sonucu gösterir (eski veri
karışmaz).

**FR-Stream-01:** Bir profil için stream listesi çekilemezse form kullanılabilir
kalır, sadece stream alanı boş + hata ikonu gösterir.

**FR-Sort-01:** Grid'de bir kolon başlığına tıklandığında veri yeniden Graylog'a
sorulmadan, mevcut veri seti üzerinde anında sıralanır.

---

## 8. Varsayımlar ve Açık Riskler

- Tüm tanımlanan Graylog sunucularının Search Scripting API'yi desteklediği
  varsayılıyor (Graylog ≥ 5.1). Daha eski bir sunucu eklenirse bağlantı testi
  bunu yakalayamayabilir — ileride profile "API uyumluluk kontrolü" eklenebilir.
- `FieldsJson` alanı şimdilik serbest metin girişi olarak tasarlandı; Graylog'un
  döndürdüğü gerçek alan adlarıyla eşleşip eşleşmediği form seviyesinde
  doğrulanmıyor (kullanıcı yanlış yazarsa boş kolon görünür, hata vermez).
- Çoklu stream seçiminde Graylog tarafı bunları OR mantığıyla birleştirir
  (Graylog'un kendi `streams` parametre davranışı) — uygulama tarafında ek bir
  mantık eklenmiyor.

---

## 9. Faz 2 Backlog (Referans)

| Özellik | Not |
|---|---|
| CSV/Excel export | Grid sonuçlarını dışa aktarma |
| Sorgu çalıştırma geçmişi | Son çalıştırma zamanı + sonuç sayısı |
| Sorgu kategorileme/klasörleme | Sorgu sayısı arttığında gerekecek |
| Tarih aralığı runtime override | Kayıtlı tanımı değiştirmeden geçici farklı aralık deneme |
