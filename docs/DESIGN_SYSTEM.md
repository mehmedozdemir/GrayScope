# DESIGN_SYSTEM.md — GrayScope

Bu dosya, `pyside6-ui-ux` skill'indeki genel tasarım sistemini bu projeye özgü
ekran/bileşen kararlarıyla somutlaştırır. Genel token'lar, durum kuralları ve
checklist için skill dosyasına bakılır — burada **sadece bu projeye özel** kararlar
yer alır.

---

## 1. Tema

- Varsayılan: **Dark theme**, `pyside6-ui-ux` skill'indeki standart token seti
  (`BG_BASE`, `BG_SURFACE`, `BG_ELEVATED`, `ACCENT`, vb.) `ui/theme.py` üzerinden
  kullanılır.
- Açık tema Faz 1 kapsamında değil.
- Tek accent rengi (`ACCENT = #5B8AF0`) — "Çalıştır", "Kaydet", "+ Yeni" gibi
  birincil aksiyonlarda kullanılır. Bir ekranda asla iki eş-ağırlıklı birincil
  buton olmaz.

---

## 2. Uygulama Kabuğu (App Shell)

```
┌──────────┬─────────────────────────────────────────┐
│          │                                           │
│ Sidebar  │              Content Stack                │
│ (240px)  │                                           │
│          │                                           │
│ Sorgular │                                           │
│ Müşteriler│                                          │
│ Profiller │                                          │
│          │                                           │
└──────────┴─────────────────────────────────────────┘
```

- Sidebar sabit genişlik 240px, `pyside6-ui-ux` Sidebar bileşeni baz alınır.
- Menü sırası sabit: **Sorgular** (varsayılan/açılış) → **Müşteriler** →
  **Graylog Profilleri**.
- Her menü öğesinde ikon + etiket; aktif öğe `ACCENT_MUTED` arka plan + `ACCENT`
  sol şerit ile vurgulanır.

---

## 3. Sorgular Ekranı — Layout

```
┌────────────────────┬──────────────────────────────────────┐
│ [Ara...]            │  <Sorgu Adı>           [✎] [🗑]       │
│ [+ Yeni Sorgu]       │                                       │
│ ─────────────────── │  Müşteri: [▾ Seç...]   [Çalıştır]     │
│ • Sorgu A  (Profil1)│  ───────────────────────────────────  │
│ • Sorgu B  (Profil2)│  | Kolon1 ▾ | Kolon2 | Kolon3 |       │
│ • Sorgu C  (Profil1)│  |  ...     |  ...   |  ...   |       │
│                      │                                       │
└────────────────────┴──────────────────────────────────────┘
   320px (min, resizable)              kalan alan (esnek)
```

- `QSplitter` (horizontal), sol panel minimum 280px / başlangıç 320px, sağ panel
  esnek genişler.
- Sol panel liste öğesi: sorgu adı (`SIZE_MD`, `WEIGHT_MEDIUM`) + bağlı profil adı
  küçük badge (`SIZE_XS`, `TEXT_SECONDARY`, `BG_ELEVATED` arka plan, `RADIUS_FULL`).
- Sol panel boşsa (hiç sorgu yoksa): empty state — "Henüz sorgu tanımlanmadı" +
  "+ Yeni Sorgu" CTA ortalanmış.
- Sağ panel hiçbir sorgu seçili değilken: empty state — "Soldan bir sorgu seçin
  ya da yeni bir sorgu oluşturun".
- "Müşteri" seçici sadece `UsesCustomerParameter = true` olan sorgularda görünür;
  `false` olanlarda bu satır tamamen gizlenir, "Çalıştır" doğrudan görünür.
- "Çalıştır" butonu, parametrik sorguda müşteri seçilmeden **disabled** (tooltip:
  "Önce bir müşteri/şehir seçin").
- Grid kolon başlığı tıklanınca küçük ok ikonu (▲ artan / ▼ azalan) gösterilir,
  sıralama client-side (`QSortFilterProxyModel`).
- Çalıştırma sırasında grid alanı skeleton/loading state'e geçer (sabit spinner
  yerine `pyside6-ui-ux` Skeleton deseni kullanılır).
- Sonuç boşsa: grid alanında empty state — "Bu sorgu için kayıt bulunamadı"
  (hata değil, bilgi tonunda).

---

## 4. Yeni/Düzenle Sorgu Dialog'u

- Modal, genişlik ~640px, dikey scrollable içerik.
- Alan sırası (PROJECT_PLAN.md §5.5 ile birebir uyumlu):
  1. Ad — `Input`
  2. Graylog Profili — `ComboBox`
  3. "Müşteri parametresi kullan" — `Checkbox`, açıldığında altında küçük bir
     bilgi notu (`SIZE_SM`, `TEXT_SECONDARY`): "Sorgu metninde `{Plaka}` yazıp
     çalıştırma anında şehir seçtirebilirsiniz."
  4. Sorgu metni — çok satırlı `TextEdit`, `font-family: var(--font-mono)` benzeri
     sabit genişlikli font (Qt'de `QFont("Consolas")` veya platform eşdeğeri)
  5. Stream seçimi — seçili profile göre canlı yüklenen çoklu seçim listesi
     (checkbox listesi + üstte arama input'u), yüklenirken skeleton, hata
     durumunda satır içi uyarı ikonu + "Yenile" linki
  6. Tarih aralığı — 3 sekmeli (`Relative` / `Absolute` / `Keyword`), her sekme
     sadece kendi alanlarını gösterir (diğerleri DOM'da gizli değil, sekme
     değişince ilgili alanlar render edilir)
  7. Gösterilecek alanlar — chip/tag input (Enter ile alan ekleme, chip üzeri X
     ile silme)
  8. Varsayılan sıralama alanı (opsiyonel `ComboBox`, alan listesinden) + yön
     (`asc`/`desc` radio buton çifti)
  9. Sonuç limiti — sayısal `SpinBox`, varsayılan 150, min 10, max 1000
  10. Alt bar: "Vazgeç" (secondary) + "Kaydet" (primary) — sağa hizalı

- Validasyon: Ad boş olamaz, Sorgu metni boş olamaz, `UsesCustomerParameter=true`
  ise sorgu metninde `{Plaka}` geçmiyorsa kaydetmeden önce satır içi uyarı
  gösterilir (engellemez, sadece uyarır — kullanıcı bilerek de eklemeyebilir).

---

## 5. Graylog Profilleri Ekranı — Layout

- Tek panel, üstte sayfa başlığı + sağda "+ Yeni Profil" CTA.
- Tablo kolonları: Ad, Sunucu Adresi, Varsayılan (badge), Aktif (badge), Aksiyonlar.
- Satır aksiyonları (ikon butonlar, tooltip'li): Düzenle, Sil, **Test Et**.
- "Test Et" tıklanınca buton spinner'a döner, sonuç `Toast` ile bildirilir
  (success: yeşil / error: kırmızı, 4 sn sonra otomatik kaybolur).
- Token alanı formda her zaman maskeli (`••••••••`), "Göster" ikonu ile geçici
  açılabilir; listede asla görünmez.
- Liste boşsa: empty state — "Henüz Graylog sunucusu tanımlanmadı" + CTA.

---

## 6. Müşteriler (Plaka) Ekranı — Layout

- Üstte arama input'u (plaka kodu veya isimle filtre) + sağda "+ Yeni Kayıt".
- Tablo kolonları: Plaka Kodu, Şehir, Aktif (badge/toggle), Açıklama, Aksiyonlar.
- `IsActive = false` satırlar `TEXT_DISABLED` rengiyle, hafif soluk görünür ama
  silinmez (toggle ile geri açılabilir).
- İlk kurulumda 81 il otomatik dolu gelir — bu nedenle bu ekranın empty state'i
  pratikte sadece arama sonucu boşsa görünür ("Aramanızla eşleşen kayıt yok").

---

## 7. İkonografi

- Tek bir ikon seti kullanılır (proje genelinde tutarlılık), Claude Code ilk
  kurulumda uygun bir PySide6-uyumlu ikon kütüphanesi seçip `ui/theme.py`
  içinde merkezi olarak tanımlar — dağınık/karışık ikon kaynağı kullanılmaz.
- Sık kullanılan ikonlar: ara, ekle (+), düzenle (✎), sil (🗑), test/bağlantı,
  artan/azalan sıralama, kapat (×), uyarı, başarı, bilgi.
- Tüm ikon-only butonlarda `setToolTip()` zorunlu (skill kuralı).

---

## 8. Bildirimler (Toast)

| Olay | Toast Tipi |
|---|---|
| Sorgu kaydedildi | success |
| Sorgu silindi | success |
| Bağlantı testi başarılı | success |
| Bağlantı testi başarısız | error |
| Sorgu çalıştırma hatası | error |
| Profil silinemedi (bağlı sorgu var) | warning |

Toast'lar `pyside6-ui-ux` skill'indeki standart konum/davranışı kullanır
(sağ-alt, 4 sn otomatik kaybolma, fade ile).
