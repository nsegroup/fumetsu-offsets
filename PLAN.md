# fumetsu/cs2-offsets — otomatik CS2 offset güncelleme sistemi

**Amaç (Celal E. Torun, 15.10.2026):** CS2 her güncellendiğinde, Choi'nin (veya
herhangi birinin) bilgisayarına gerek kalmadan, tamamen GitHub Actions bulutunda
taze offsetleri üret, imzala, `fumetsu.cc` üzerinden yayınla. FUMETSU DLL inject
anında offsetleri `fumetsu.cc`'den çeker, imzayı doğrular, bağlar ve çalışır.

İnternet her zaman var kabul edilir — offline/fallback yok. `fumetsu.cc` tek
offset kaynağıdır.

---

## Mimari

```
Valve CS2 günceller
      │
      ▼  (GitHub Actions cron, ~10 dk)
[1] check_build.py  ── Steam public build id'yi sorgular
      │  değişti mi?  hayır → çık (noop)
      ▼  evet
[2] DepotDownloader (ANONİM, app 730)  ── client.dll, engine2.dll, steam.inf çeker
      │
      ▼
[3] DUMP (oyun ÇALIŞMADAN, headless runner):
      ├─ source2gen   → schema offsetleri (classes/* : m_iHealth vb., buttons)
      └─ cs2-dumper   → modül global'leri (dwEntityList, dwViewMatrix, dwBuildNumber…)
      │
      ▼
[4] make_offsets.py  ── hepsini data.json şekline birleştirir
      │                 (offsets_flat + classes + buttons + build)
      ▼
[5] sign.py          ── ed25519 ile imzalar (özel anahtar = Actions secret)
      │                 envelope: {build, kid, payload_b64, sig_b64}
      ▼
[6] yayınla:
      ├─ repoya commit: offsets/by-build/<build>.json, offsets/latest.json
      └─ fumetsu.cc origin bu dosyayı sunar (/data.json → latest.json)
      │
      ▼
FUMETSU DLL (inject):
  canlı build no oku → fumetsu.cc/data.json çek → ed25519 imza + kid + build doğrula
  → offsetleri sdk:: değişkenlerine bas → çalış
  (doğrulama/çekme başarısızsa: compiled default ile devam + uyarı — ASLA çökme)
```

## Neden bu en güçlü yöntem

- **Bağımsızlık:** a2x'in output'unu *yayınlamasını* beklemeyiz; a2x'in dumper
  **kodunu** (imzalar nadiren değişir) kendimiz depot güncellenir güncellenmez
  çalıştırırız. Rakipten/mirror'dan önce taze oluruz.
- **Oyunsuz:** source2gen client.dll'i `LoadLibrary` ile yükleyip schema sistemini
  çağırır; cs2-dumper offline/dosya modunda PE'yi imza taramasıyla okur. Çalışan
  oyuna / GPU'ya / anti-cheat'e gerek yok → headless CI'de koşar.
- **Anonim depot:** app 730 anonim Steam login ile iner, hesap/sahiplik gerekmez.

## Güvenlik

- Repo **private**. Yine de imza zorunlu: yayınlanan her payload ed25519 ile
  imzalanır. Özel anahtar YALNIZCA `secrets.OFFSET_SIGNING_KEY` olarak yaşar,
  repoya asla girmez. Public anahtar DLL'e gömülü (`kOffsetPubKey`, kid
  `45d4bb8bafbf9ee0`).
- DLL imzası geçmeyen, kid tutmayan veya canlı build ile eşleşmeyen hiçbir
  payload'ı uygulamaz.
- **Fail-closed:** dump adımı global'leri çözemezse pipeline durur ve issue açar,
  bozuk offset YAYINLAMAZ. (sdk_fetch geçmişindeki "stale overwrite" kazası böyle
  önlenir.)

## Validasyon notu

Depot indirme ve iki dumper'ın derlenip koşması yalnızca gerçek GitHub Actions
runner'ında (Windows + internet + Steam) doğrulanabilir; bu sandbox'ta koşturulamaz.
İlk `workflow_dispatch` çalıştırması pipeline'ı uçtan uca doğrular.
