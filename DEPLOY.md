# Deploy sang máy khác (Docker) — KNXStore Content/Registry Tools

Hướng dẫn deploy toàn bộ project (Track A — Registry Diff sản phẩm KNX/Matter, Track B —
Content/blog) sang 1 máy khác (vd. Mac Mini production), dùng chung Docker cho Postgres.

**Đọc kỹ mục 5 trước khi chạy bất cứ gì** — đó là bước dễ bị bỏ sót nhất và sẽ làm mất toàn
bộ 36 nguồn blog đang hoạt động (kể cả nguồn tự thêm qua UI) nếu quên.

---

## 0. Yêu cầu máy đích

- Docker Desktop (hoặc OrbStack) — đã cài, **đang chạy** trước khi bắt đầu.
- Python 3.9+ (đã test với 3.9), `pip3`.
- Git.
- `claude` CLI (Claude Code) đã login — **chỉ cần nếu dùng B3 triage** (`track-b/src/
  triage_articles.py`), không cần cho crawl/fetch thông thường.

## 1. Clone code

```bash
git clone https://github.com/spaceCadetVUX/web_data_collection_and_analysis_tools_knxstoreVn.git
cd web_data_collection_and_analysis_tools_knxstoreVn
```

## 2. Tạo file `.env` (KHÔNG có trong git — chứa credential)

```bash
cp track-a/src/.env.example track-a/src/.env
```

Sửa `track-a/src/.env`, đổi `POSTGRES_PASSWORD` thành mật khẩu thật (không dùng
`changeme`). Giữ nguyên `POSTGRES_PORT=5433` trừ khi máy đích đã dùng cổng này cho việc
khác.

## 3. Chạy Postgres qua Docker

```bash
cd track-a/src
docker compose up -d
cd ../..
```

Kiểm tra container đã chạy: `docker ps --filter name=registry-postgres`.

## 4. Áp dụng TOÀN BỘ migration theo đúng thứ tự số

```bash
DB="postgresql://registry_admin:<mật khẩu bạn đặt ở bước 2>@localhost:5433/knxstore_registry"

for f in $(ls track-a/migrations/*.sql | grep -v '\.down\.sql$' | sort); do
  echo "=== $f ==="
  docker exec -i registry-postgres psql -U registry_admin -d knxstore_registry -f /dev/stdin < "$f"
done
```

⚠️ **Chú ý `grep -v '\.down\.sql$'`** — bắt buộc phải loại các file `*.down.sql` (rollback,
dùng để XOÁ ngược lại) ra khỏi vòng lặp. Nếu glob ăn nhầm cả file down (vd. dùng
`track-a/migrations/000*.sql` — cũng khớp `.down.sql` vì đuôi vẫn là `.sql`), migration vừa
tạo xong sẽ bị DROP ngay lập tức ở dòng lệnh kế tiếp — đã tự kiểm tra kỹ trước khi viết file
này (2026-08-15), lệnh trên đã test đúng.

Lệnh trên chạy đúng thứ tự 0001 → 0015 (schema + seed brand + seed nguồn gốc + các bản vá
selector). **Không được bỏ qua file nào, không được đảo thứ tự** — file sau phụ thuộc bảng/
cột do file trước tạo.

## 5. ⚠️ QUAN TRỌNG — khôi phục đúng 36 nguồn ĐANG hoạt động (không chỉ 35 nguồn gốc)

Migration 0005/0008/0010/0013 chỉ tạo ra **35 nguồn gốc lúc mới build** — sau đó có 2 thay
đổi làm bằng tay trực tiếp trên DB (không nằm trong migration nào):
- Sửa URL `csa-iot-newsroom` (từ `/newsroom/page/4/` — đã 404 — sang `/newsroom/` đúng)
- Thêm nguồn `thv` (The Verge — Apple, `kind=html_list`, đã cấu hình đúng selector)

Nếu chỉ chạy migration ở bước 4, máy đích sẽ có **35 nguồn cũ, thiếu 1 nguồn, sai 1 URL** —
không đúng trạng thái đang hoạt động thật.

→ Chạy thêm file snapshot này SAU KHI đã chạy xong bước 4:

```bash
docker exec -i registry-postgres psql -U registry_admin -d knxstore_registry -f /dev/stdin \
  < track-a/migrations/snapshots/news_sources_snapshot_2026-08-15.sql
```

File này tự `TRUNCATE news.sources` trước khi insert lại đúng 36 dòng hiện tại — **chạy lại
nhiều lần vẫn an toàn** (idempotent), không sợ chạy nhầm 2 lần.

**Mỗi khi thêm/sửa nguồn qua UI Settings sau này, nhớ xuất lại snapshot mới trước khi deploy
lần sau** (xem mục 8 — Cách xuất snapshot mới), nếu không máy mới sẽ lại thiếu nguồn mới nhất.

## 6. Cài Python dependencies

3 chỗ riêng, mỗi chỗ có `requirements.txt` khác nhau (KHÔNG dùng chung 1 venv là bắt buộc,
nhưng cài đủ cả 3 để mọi tính năng chạy được):

```bash
python3 -m pip install -r track-a/webapp/requirements.txt   # webapp (dashboard, /content, settings...)
python3 -m pip install -r track-a/src/requirements.txt        # crawler KNX/Matter
python3 -m pip install -r track-b/src/requirements.txt        # crawler blog + trafilatura
```

## 7. Chạy webapp

```bash
cd track-a/webapp
./run_webapp.sh
```

Mở `http://localhost:8800` — kiểm tra:
- `/` (Product Track A) — nếu chưa import baseline KNX/Matter thì Products sẽ rỗng, xem
  mục 9 (tùy chọn) nếu cần dữ liệu sản phẩm luôn.
- `/content` — phải thấy **36 nguồn** (nếu bước 5 làm đúng).
- `/settings` — mục "Nguồn crawl content — Track B" cũng phải ra 36.

## 8. Cách xuất snapshot MỚI (dùng cho lần deploy sau, khi đã thêm/sửa nguồn)

```bash
docker exec registry-postgres pg_dump -U registry_admin -d knxstore_registry \
  --data-only --inserts --column-inserts --table=news.sources \
  > track-a/migrations/snapshots/news_sources_snapshot_$(date +%F).sql
```

Sau đó tự thêm 1 dòng `TRUNCATE news.sources RESTART IDENTITY CASCADE;` ngay trước dòng
`-- Data for Name: sources` trong file vừa xuất (xem file mẫu `news_sources_snapshot_
2026-08-15.sql` để biết định dạng), rồi commit file này vào git.

## 9. (Tùy chọn) Import baseline sản phẩm KNX/Matter thật (15k+ thiết bị)

CSV baseline có sẵn trong git (`track-a/data/*.csv`), nhưng KHÔNG tự động vào DB — phải chạy
tay:

```bash
cd track-a/src
python3 import_and_diff.py --db-url "$DB" --csv ../data/knx_devices_baseline.csv --registry-key knx
python3 import_and_diff.py --db-url "$DB" --csv ../data/matter_devices_baseline.csv --registry-key matter_csa
```

## 10. Việc KHÔNG tự động theo qua máy mới — cần biết trước

| Dữ liệu | Có theo không? |
|---|---|
| Schema, 36 nguồn blog, 73 brand quan tâm | ✅ Có, nếu làm đúng bước 4+5 |
| CSV baseline KNX/Matter | ✅ Có trong git, nhưng phải chạy tay bước 9 |
| **545 bài đã crawl** (`news.articles`) | ❌ KHÔNG — chỉ có trên máy dev hiện tại, cần `pg_dump`/`pg_restore` toàn bộ DB nếu muốn giữ (xem mục 11) |
| Kết quả triage đã chạy (`news.analysis`) | ❌ KHÔNG — tương tự trên |
| Lịch sử `fetch_log`/`crawl_log`/`digest_log` | ❌ KHÔNG |
| Setting đã chỉnh (số trang lật, mốc ngày lọc ở `/content`) | ❌ KHÔNG — về lại mặc định (5 trang, không lọc ngày) |
| Credential Zalo KHub, Claude API key | ❌ KHÔNG — chưa có trên cả máy dev, cần điền vào `track-a/webapp/zalo.py` và biến môi trường Claude khi có |

## 11. (Tùy chọn, nếu muốn giữ luôn cả 545 bài + lịch sử) — backup/restore toàn bộ DB

```bash
# Máy cũ (dev):
docker exec registry-postgres pg_dump -U registry_admin -Fc knxstore_registry > full_backup.dump

# Máy mới, SAU KHI đã docker compose up -d (bước 3), TRƯỚC KHI chạy migration (bước 4):
docker cp full_backup.dump registry-postgres:/tmp/full_backup.dump
docker exec registry-postgres pg_restore -U registry_admin -d knxstore_registry --clean --if-exists /tmp/full_backup.dump
```

Nếu làm cách này thì **BỎ QUA bước 4 và 5** — restore toàn bộ đã bao gồm hết schema + data
mới nhất, không cần chạy migration riêng nữa.

## 12. Lưu ý vận hành (macOS)

- Mac không được sleep nếu muốn scheduler (`APScheduler` trong webapp) chạy đúng giờ đã đặt
  ở Settings — kiểm tra `pmset -g | grep sleep`, cân nhắc `sudo pmset -a disablesleep 1`.
- Docker Desktop cần bật "Start Docker Desktop when you sign in" nếu máy khởi động lại.
- Docker Desktop có thể bị treo (daemon không phản hồi dù process vẫn sống) — gặp thật trên
  máy dev ngày 2026-08-15. Cách xử lý: `pkill -9 -f "Docker Desktop"` rồi `open -a "Docker
  Desktop"`, đợi ~10-20s cho daemon sống lại (không mất data vì Postgres dùng named volume).
