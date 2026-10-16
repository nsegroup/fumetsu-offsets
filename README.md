# fumetsu/cs2-offsets

CS2 güncellenir güncellenmez taze offsetleri **tamamen GitHub Actions bulutunda**
(Choi'nin / kimsenin PC'si olmadan) üretip imzalayıp `fumetsu.cc` üzerinden yayınlar.
FUMETSU DLL inject anında offsetleri `fumetsu.cc`'den çeker, ed25519 imzasını
doğrular, bağlar. Mimari için **PLAN.md**.

## Repo private. Kurulum (tek seferlik)

1. **Bu klasörü private repo olarak push et:**
   ```
   gh repo create fumetsu/cs2-offsets --private --source . --push
   ```
2. **İmzalama anahtarını secret olarak ekle** (özel tohum, 32 byte base64):
   ```
   gh secret set OFFSET_SIGNING_KEY --repo fumetsu/cs2-offsets --body "<SEED_B64>"
   ```
   Tohum anahtar üretildiğinde ayrı verildi; repoya **asla** girmez.
   Public anahtar DLL'e gömülü (`src/sdk_fetch.h` → `kOffsetPubKey`,
   kid `45d4bb8bafbf9ee0`).
3. (İsteğe bağlı) `fumetsu.cc` deploy hook'u: `gh secret set FUMETSU_DEPLOY_HOOK ...`.
   Ayarlanmazsa `fumetsu.cc`, repodaki `offsets/latest.json`'ı `/data.json` olarak
   sunacak şekilde yapılandırılır.
4. İlk uçtan uca doğrulama: Actions → **cs2-offsets** → **Run workflow**.

## Çalışma

- `.github/workflows/offsets.yml` her 10 dk'da bir `check_build.py` ile CS2 public
  build id'yi sorgular. Değişmişse: DepotDownloader (anonim) client.dll/engine2.dll
  indirir → offline dump → `make_offsets.py` birleştirir → `sign.py` imzalar →
  `offsets/latest.json` + `offsets/by-build/<build>.json` commit'lenir.
- **Fail-closed:** dump zorunlu offsetleri çözemezse `make_offsets.py` hata verir,
  hiçbir şey yayınlanmaz ve otomatik issue açılır. Bozuk/eksik offset asla
  yayınlanmaz.

## DLL tarafı (FUMETSU reposunda)

`src/sdk_fetch.h::FetchOffsets()` inject'te çağrılır: envelope'u çeker, kid +
ed25519 imza + canlı build eşleşmesini doğrular, sonra global/engine/button
offsetlerini `sdk::` değişkenlerine basar. Doğrulama veya çekme başarısızsa
compiled default'larla devam eder — **asla çökmez**.

## Not

Depot indirme ve dumper'ın derlenip koşması yalnızca gerçek runner'da
(Windows + internet + Steam) doğrulanır; ilk `workflow_dispatch` ile teyit edilir.
Kripto sözleşmesi (sign.py ↔ DLL public key) ve `make_offsets.py` birleştirme
yerelde doğrulandı.
