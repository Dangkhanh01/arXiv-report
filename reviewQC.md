# QC Milestone 1 — Trạng thái sau sửa

Cập nhật: **01/11/2026 (Asia/Ho_Chi_Minh)**. Thay đổi đang nằm trong working tree của report repository, dựa trên commit `4f06acf`; chưa commit/push/deploy.

**Đã sửa các lỗi code và diễn giải có thể xử lý trong workspace, có kiểm tra hồi quy. Chưa thể chứng nhận các bằng chứng lịch sử không có dữ liệu gốc.** Các mục thiếu bằng chứng được hiển thị đúng là unknown/not measured, không điền hằng số và không đánh dấu đã đạt yêu cầu benchmark cuối.

## 1. Các lỗi đã sửa và vị trí hiện tại

Số dòng là dòng vật lý trong source hiện tại; với `.ipynb` là JSON source, không phải số cell trong Jupyter. Phần lịch sử cuối file dùng số dòng của snapshot trước sửa.

| QC | Kết quả sửa | Source chính |
|:---|:---|:---|
| A — Coverage/fallback | Thêm assignment manifest độc lập, tính missing/unexpected/metadata coverage/wrong-member từ tập ID; notebook kiểm tra schema và đối chiếu dữ liệu trước render, bỏ fallback số lịch sử | `config/assignments.json`; `scripts/aggregate_data.py`, `assignment_coverage()`; `scripts/report_checks.py`, `load_report_data()` |
| B — Dung lượng corpus | Bỏ hằng số 7.381.815.495 bytes/360.917 files. Summary lưu null và Book hiển thị **Not measured**. Nếu có corpus ZIP, kiểm tra corpus receipt/hash/size/CRC riêng; không dùng ZIP entry sizes làm filesystem measurement | `scripts/aggregate_data.py`, phần corpus verification; `04_performance.ipynb`, Multi-Run Benchmark Results |
| C — References observed | Bỏ cộng 100/partial và fallback +300. Đếm observed từ actual all-reference store hoặc total đã xác định; unknown vẫn null. Retained data có lower bound **734.320**, không gọi là tổng đầy đủ. Ghi đúng non-arXiv 367.904 thuộc nhóm known-total | `scripts/aggregate_data.py`, reference snapshot/counts; `03_corpus_stats.ipynb`, KPI; `04_performance.ipynb`, handoff |
| D — Provenance/CPU-only | Tách report/corpus verification; wording dùng **retained flags/verification records**, không nói hash chứng minh accelerator=None. Giữ nguyên flags được lưu; không chứng nhận lại upstream environment | README, index, Overview, Methodology và cả hai notebook |
| E — Authors/field audit | Bỏ literal authors 100%. Hiện audited/present/missing/unknown theo field. Khi ingest có metadata/reference stores thì tính field-presence audit từ input; retained CSV không có trường thì báo unknown | `summary.json.metadata_field_audit`; `03_corpus_stats.ipynb`, Field presence audit |
| F — Failure handoff | Bỏ tuyên bố recheck/giữ raw tar/giữ corrupt payload và hứa triển khai M2 khi chưa có bằng chứng. Bảng tách observed/proposed action/current status/impact. Giữ failed; không suy 404=no_tex | `03_corpus_stats.ipynb`, Failure Disposition and Downstream M2 Handoff Matrix |
| G — Performance scope | Giữ distinction machine-hours/post-discovery/RAM sampling; công bố capacity và tracked paths chưa được xác nhận. Thiếu resource measurements không bị biến thành 0. Chưa kết luận đạt disk capacity/testbed | `04_performance.ipynb`; `benchmark.json` |
| H — Expected version tăng qua checkpoint | Merge expected từ input/record versions; số version rows không thay expected history; thêm `versions_missing`. Fixture expected=3 nhưng mới có v1/v2 được giữ unresolved | `scripts/aggregate_data.py`, paper merge và version reconciliation |
| I — Non-arXiv vào pool / stale union | Chỉ ID arXiv hợp lệ vào pool; giữ nguyên all-store riêng để đếm observed. Pool và counters cùng selected snapshot, đối chiếu kept count; không union citations từ retries | `scripts/aggregate_data.py`, reference snapshot selection |
| J — Manifest run mismatch | So run ID của manifest/receipt/folder và CSV/benchmark khi có run ID; mismatch dừng ingestion | `scripts/aggregate_data.py`, archive schema/run validation |
| K — Input hỏng bị bỏ qua | Required manifest/papers/versions/benchmark phải có và đọc hợp lệ; schema/counter/duplicate/orphan checks; parse lỗi không còn biến thành dữ liệu rỗng rồi tiếp tục | `scripts/aggregate_data.py`, ZIP parsers và ingestion |
| L — Ghi đè nửa bộ output | Tạo snapshot ở sibling staging; chỉ publish khi mọi validation thành công. Ordinary publication failure rollback bộ dữ liệu cũ. Không ingest cây rỗng đè dữ liệu | `scripts/aggregate_data.py`, `aggregate_corpus()` |

Các sửa đúng ở review trước vẫn được giữ: cận histogram `inf`, đủ 20.000 paper; unknown chia theo 3 partial/1 failed/33 not_found; tên selected/benchmark runs; case-collision không suy OS; offset-based pagination.

`sync_data.py` cũ có thể bypass receipt checks và copy thiếu file; đã chuyển thành entry point dùng cùng ingestion transaction/schema validation. Nó nhận cây member/account/Milestone1 như aggregator, không còn tự chọn một ZIP rồi ghi đè một phần report. README đã cập nhật thay đổi tương thích này.

## 2. Kiểm chứng sau sửa

- **29/29 tests pass**: 11 kiểm tra cũ và 18 kiểm tra hồi quy/validation mới. Test dùng ZIP thật và receipts cập nhật đúng hash/size, không mock nội dung ingestion để tạo kết quả mong muốn. Có test rollback khi publish bị lỗi.
- **Strict Book build pass**: `.venv/bin/jupyter-book build --all -W --keep-going book`; cả hai notebook thực thi lại thành công. Log tại `/tmp/arxiv-qc-fixed-build.log`; tests log tại `/tmp/arxiv-qc-fixed-tests.log`. Kernel có thông báo transport TCP; không coi đó là lỗi nội dung/build.
- Syntax cells tương thích **Python 3.11** dùng trong GitHub Actions; local interpreter là Python 3.14.
- Kiểm tra nội dung HTML đã render: có **Not measured / Not established**, lower bound 734.320 và failed disposition; không còn output các tuyên bố authors 100%, 734.457 observed, 6.87 GiB/360.917 files hay “Zero parse impact”. Đây là kiểm tra HTML output, chưa thay thế visual/browser QA trên bản public.
- `load_report_data()` đối chiếu CSV với summary, assignment manifest, reference counts/denominator/mean, version outcomes, run sets và member counts trước khi notebook render. Histogram dùng chung implementation giữa Book và regression test.
- CI workflow đã thêm tests trước deploy và dùng strict build, tránh deploy nếu regression/build thất bại.
- Không thay các paper/version CSV lịch sử. Chỉ sửa fields summary/benchmark suy ra được hoặc đang thiếu bằng chứng. Giữ 20.000 paper, 27.608 version, 131 failed/115 paper và các retained source/time/resource counters đã có.

## 3. Các mục còn cần evidence/input thật

| Mục | Còn thiếu | Trạng thái trung thực trong report |
|:---|:---|:---|
| Final output filesystem size | Corpus gốc, policy chọn/merge snapshot, cây corpus đã hợp nhất và phép đo bytes/file count/coverage/ngày | **Not measured**, chưa đạt yêu cầu final storage measurement |
| Historical source/report provenance | Archive/receipt gốc để đọc lại và xác minh; log hiện tại chỉ ghi 201 report ZIP entries | Retained verification records; không chứng nhận lại lịch sử |
| CPU-only final benchmark | Benchmark/environment gốc gắn đúng run, hoặc benchmark mới trên Colab CPU-only có evidence | 107/107 retained flags=True; chưa independent re-verification |
| Observed references đầy đủ | Actual all-reference stores/receipts cho unknown outcomes | Exact corpus-wide observed total null; lower bound 734.320 |
| Metadata quality | Authors/revisions/reference stores và mẫu expected/observed/upstream có ngày/nguồn | Field chưa audit là unknown; completeness counters chỉ nói về arXiv matching pool |
| 131 failed versions | Recheck/recovery evidence nếu quyết định phục hồi; không đủ dữ liệu để sửa source từ report | Giữ failed/unresolved và bảng proposed actions |
| Disk capacity/scope | Runtime capacity và exact tracked paths của các run lịch sử | Chưa xác minh; không kết luận nằm trong capacity limit |
| Public delivery | Pages deployment đúng commit, public access và browser render/Plotly/MathJax | Chưa push/deploy hoặc xác minh public trong đợt sửa local này |

Không thể khôi phục bằng chứng lịch sử hoặc source thất bại bằng cách chỉnh Markdown/JSON. Muốn đóng những mục này cần input thật; code hiện đã ngăn việc thiếu input bị che bằng số liệu cũ. Không có tuyên bố bảo đảm tuyệt đối không còn bug; kết quả ở trên dựa vào regression tests, đối chiếu retained data và strict build đã chạy.

## 4. Cách kiểm tra lại

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/jupyter-book build --all -W --keep-going book

# Khi có input thật: ingest sang target riêng để review trước khi thay book/data.
.venv/bin/python scripts/aggregate_data.py --source /path/to/input --target /path/to/review-snapshot
```

Chạy một writer tại một thời điểm và build sau ingestion. Directory swap không phải cơ chế đồng bộ nhiều process; nếu bị ngắt đúng lúc publish, backup sibling `.data-previous` được giữ để recovery. Lỗi ingestion hoặc ordinary publish failure đã có test giữ nguyên target cũ.

---

<details>
<summary>Lịch sử review trước khi sửa — giữ nguyên để truy vết, không phải trạng thái hiện hành</summary>

# Rà soát lại Jupyter Book Milestone 1 sau đợt sửa QC

Ngày kiểm tra: **01/11/2026 (Asia/Ho_Chi_Minh)**. Bản được kiểm tra: report commit `4f06acfde210700114fce142268c49078eb1972d` và mã crawler trong workspace hiện tại.

**Kết luận: chưa đủ cơ sở đóng toàn bộ 14 mục QC.** Đã có các sửa đổi đúng về histogram, tên/phạm vi run, case collision và pagination. Tuy nhiên còn số đo nhập cứng, thiếu bằng chứng corpus/environment và các khẳng định handoff/metadata vượt quá bằng chứng lưu trong repository. **11/11 tests pass và Book build pass không xác nhận các khẳng định đó.**

Phần đánh giá ngày 01/11 dưới đây thay thế trạng thái “ĐÃ XỬ LÝ TRIỆT ĐỂ TOÀN BỘ 14 MỤC QC” ở bản trước. Nội dung rà soát ban đầu được giữ cuối file làm lịch sử; các trạng thái và số dòng ở phần lịch sử không phải trạng thái hiện hành.

## 1. Phạm vi và cơ sở đối chiếu

- Đề lưu tại `../ARXIV_PROJECT_FULL.md`, đặc biệt phần M1 **Requirement**, **Report Requirements (Jupyter Book)** và **Grading Criteria**. Đã mở lại [đề M1 của môn học](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/) ngày 01/11; các yêu cầu được dùng cho lượt review này tương ứng với bản lưu.
- Đọc Overview, Methodology, toàn bộ source cells của hai notebook, `_toc.yml`, `_config.yml`, README, workflow deploy, aggregator, tests và dữ liệu đo được commit.
- Đối chiếu implementation với `../src/crawling/{assignments,download,references,pipeline,metrics}.py` khi cần phân biệt hành vi thực tế với diễn giải trong report.
- Workspace này không có cây `input/` gốc tại các vị trí mặc định của aggregator. Đường dẫn archive trong `run_metadata.json` trỏ đến máy Windows của lần tổng hợp trước. Vì vậy lượt này **không xác minh lại SHA-256 của ZIP lịch sử**, không đọc lại metadata trong corpus gốc và không chạy lại crawler/network benchmark.
- Chỉ phần M1 được publish theo TOC hiện tại. M2/M3 đang bị loại khỏi build; không xem các trang placeholder đó là report M2 đã hoàn tất. Nếu nộp M2, phải review riêng phần yêu cầu M2.

## 2. Trạng thái hiện tại của 14 mục cũ

| Mục cũ | Trạng thái sau kiểm tra lại | Kết quả và việc còn lại |
|:---|:---|:---|
| 1. `kept > total` / references unknown | **Đã sửa dữ liệu hiện tại; còn vấn đề đo lường/tái sinh** | Ba paper partial đã để total rỗng, kept lần lượt 77/8/78; bất biến trên các total xác định đạt. Còn giả định 100 refs/partial và phạm vi tổng quan sát; xem phát hiện C. |
| 2. Histogram bỏ sót >1000 refs | **Đã sửa trong notebook và CSV hiện tại** | Cận cuối `inf`, có nhóm unknown, đủ 20.000 paper. Nhóm unknown thực tế là **37 = 3 partial + 1 failed + 33 not_found**, không chỉ 3. |
| 3. Selected runs / benchmark runs | **Đã sửa với dữ liệu hiện tại** | 75 selected runs và 107 benchmark runs được tách nhãn; breakdown 18/21/18/18 và 35/29/23/20 theo Danh/Khang/Khánh/Nguyên. `ID Record Coverage` đã đổi đúng. |
| 4. Fallback và discovery coverage | **Chưa đóng** | Vẫn có fallback số lịch sử và coverage/missing/unexpected nhập cứng. Bộ ID hiện tại khớp assignments, nhưng code không tự kiểm tra điều đó; xem A. |
| 5. Case collision suy ra Windows | **Đã sửa nhãn** | Đã mô tả collision theo case-insensitive normalization, không suy ra OS. Không đồng nghĩa các tuyên bố phục hồi archive trong bảng handoff đã có bằng chứng. |
| 6. Cursor vs offset pagination | **Đã sửa** | Methodology đã ghi returned `next` offset, phù hợp implementation. |
| 7. CPU-only | **Đã bổ sung flags; bằng chứng nguồn chưa kiểm chứng lại** | JSON hiện có `true` cho 107/107 runs; không còn đúng khi nói 0/107 như review cũ. Tuy nhiên hash receipt không tự chứng minh Hardware Accelerator=None; cần liên kết flags với nội dung benchmark/environment gốc; xem D. |
| 8. Archive provenance | **Đã bổ sung log report ZIP; chưa đủ cho tuyên bố source/report** | 107 run entries chứa **201 archive records, tất cả là `report.zip`**. Không có corpus ZIP verification trong hàm verifier hiện tại; xem D. |
| 9. Dung lượng corpus cuối | **Chưa đóng** | Có số 7.381.815.495 bytes/360.917 files, nhưng code fallback chính số này nếu không có corpus, nuốt lỗi đọc ZIP và chỉ cộng central-directory sizes; xem B. |
| 10. Metadata audit | **Đã bổ sung counters; chưa đầy đủ** | Title/date có thể đếm lại; authors 100% đang là chuỗi nhập cứng. Chưa có audit theo trường của revisions/reference metadata và đối chiếu mẫu upstream; xem E. |
| 11. 131 failed versions | **Đã thêm ma trận; cần sửa nội dung** | Ma trận có khẳng định đã recheck 404, giữ raw tar/corrupt samples và sẽ sửa loader M2, chưa có log/manifest đi kèm; xem F. |
| 12. Public Pages | **Chưa xác minh** | Có repo URL/workflow; web tool lượt này không truy cập được Pages. Không kết luận site hỏng hoặc repo private. |
| 13. Phạm vi benchmark | **Nhiều giới hạn đã diễn giải đúng; còn điều kiện cần công bố** | Đã tách machine-hours, post-discovery latency, mean RAM không trọng số, thinned trace. Cần giữ rõ phần final export/backup bị loại và bổ sung disk capacity/scope để đối chiếu Colab; xem G. |
| 14. Tests/build | **Đạt chạy; chưa đủ bảo vệ các lỗi còn lại** | Đã chạy lại 11 tests và strict Book build. Các tests kiểm tra flags hiện có chưa xác minh nguồn của flags; fixture 1 paper vẫn pass dù coverage/dung lượng sai. |

## 3. Các phát hiện cần xử lý

### A. [Cao] Coverage vẫn là hằng số và fallback cũ vẫn tồn tại

**Vị trí:** `scripts/aggregate_data.py:778–784`; `03_corpus_stats.ipynb`, cell KPI/Team Member/Coverage audit; `04_performance.ipynb`, cell Multi-Run Benchmark Results.

Aggregator vẫn xuất:

```python
"id_discovery_coverage": 1.0,
"assigned_ids_target": 20000,
"missing_assigned_ids_count": 0,
"unexpected_ids_count": 0,
```

Đã tái hiện bằng fixture receipt hợp lệ chỉ có **1 paper**: kết quả vẫn `coverage=1.0`, `target=20000`, `missing=0`, `unexpected=0`. Không có phép so sánh tập ID với assignments trong đoạn tạo summary. Notebook cũng in cứng “0 missing, 0 unexpected”.

Các fallback còn lại gồm `paired_tex_versions_count=26234`, average bytes `4724372.6`/`206770.9`, reduction `0.9562`, `total_refs_confirmed + 300`, retained-source bytes `5424427008`, cùng nhiều default 0. Schema validation mới chỉ kiểm tra một phần keys, chưa ngăn các đường fallback này. Vì vậy câu “xóa toàn bộ số fallback cứng” trong phần cập nhật trước là sai.

**Điểm đã xác nhận tích cực:** lượt review này tự sinh expected ID set từ `GROUP_ASSIGNMENTS` và `VERIFIED_MONTH_END_IDS`, so với CSV hiện tại được **20.000/20.000 ID, 0 missing, 0 unexpected, 0 sai thành viên**. Đây là kiểm tra hiện trạng, không thay thế việc triển khai kiểm tra trong aggregator.

**Cần sửa:** truyền/đọc một assignment manifest có version, tính tập missing/unexpected và coverage thật; phân biệt input mẫu với corpus đầy đủ. Các KPI bắt buộc phải fail khi thiếu hoặc hiển thị “not measured”; các KPI suy ra được cần tính và đối chiếu dữ liệu. Thêm regression đầu vào thiếu một ID và thêm một ID ngoài phạm vi; thiếu KPI không được hiện lại số lịch sử.

### B. [Cao] Dung lượng “Complete Merged Output on Filesystem” chưa được đo như nhãn mô tả

**Vị trí:** `scripts/aggregate_data.py:882–896`; `04_performance.ipynb`, cell Multi-Run Benchmark Results và Storage.

Khi không tìm được file corpus nào, code xuất nguyên hằng số **7.381.815.495 bytes và 360.917 files**. Fixture 1 paper không có `corpus.zip` cũng xuất đúng hai con số này. Notebook tiếp tục fallback chuỗi “6.87 GiB (360,917 files)” nếu field thiếu.

Ngay cả khi ZIP có mặt, code chỉ đọc `ZipInfo.file_size`, gộp bằng tên entry và ghi đè theo thứ tự vòng lặp. Nó chưa:

- Xác minh corpus ZIP với corpus entry trong backup receipt, kiểm tra payload/CRC hay ghi rõ ZIP bị thiếu/lỗi; `except Exception: pass` che mất lỗi.
- Chứng minh các snapshot cùng đường dẫn được chọn khớp selected source/reference outcomes; chưa phát hiện nội dung xung đột cùng path.
- Đo cây corpus cuối trên filesystem, lưu ngày đo, phạm vi paper/version và logical/allocated bytes.

**Cần sửa:** bỏ fallback, báo unknown khi không có corpus; không nuốt lỗi. Nếu chỉ dùng ZIP inventory, đặt tên metric đúng là “deduplicated ZIP-entry logical-byte estimate”, kèm selection/conflict/coverage evidence. Muốn giữ nhãn “Complete Merged Output on Filesystem”, hợp nhất corpus theo policy xác định, xác minh archive và đo cây kết quả thật. Không cộng checkpoint trùng và không tự hiểu 201 report ZIP là 201 corpus ZIP.

### C. [Vừa] Phần references đã sửa lỗi gốc nhưng thêm giả định 100 refs/partial

**Vị trí:** `scripts/aggregate_data.py:657–681`; `03_corpus_stats.ipynb`, cell KPI/Reference Mining; `02_methodology.md`, Dual-Store Architecture; `summary.json`.

Tính lại từ CSV hiện tại:

| Phép đo | Kết quả |
|:---|---:|
| Paper có total xác định | 19.963, tất cả reference_status=success |
| Paper total unknown | 37 = 3 partial + 1 failed + 33 not_found |
| Tổng references xác định | 734.157 |
| Mean trên 19.963 paper đó | 36,77588538796774 |
| Kept arXiv ở 3 partial paper | 163 |
| Tổng arXiv pool | 366.416 |
| arXiv pool thuộc nhóm total xác định | 366.253 |
| Non-arXiv thuộc nhóm total xác định | 367.904 |

Các con số confirmed và phép chia hiện tại khớp nhau; không tiếp tục gắn lỗi số học cũ cho donut. Tuy nhiên `observed_partial_refs = sum(100 for ... status == 'partial')` không đọc số citations thực tế từ citation stores. `partial` có thể do pagination, metadata thiếu, date resolution hoặc conflicts; không chứng minh luôn có đúng 100 citations. Nếu partial có total xác định nhưng metadata chưa hoàn chỉnh, phép cộng này còn có thể đếm thêm lần nữa.

**734.457 observed và 36,72285 observed/paper hiện phụ thuộc giả định +300**, chưa được kiểm chứng lại từ stores trong workspace. Nếu thật sự quan sát 300 refs ở partials, 137 trong đó là non-arXiv; corpus-wide observed non-arXiv khi ấy là **368.041**, trong khi 367.904 chỉ thuộc nhóm confirmed. Phần handoff cuối `04_performance.ipynb` đang gọi 367.904 là “corpus-wide non-arXiv reference count”, cần sửa phạm vi hoặc dùng số đã audit đúng.

Histogram đã đếm đủ nhưng nhóm “Partial / Unknown” chứa 37 paper. Phần tóm tắt trước ghi chỉ 3 là thiếu 34 outcome còn lại. Có thể tách ba trạng thái để người đọc không hiểu nhầm mọi unknown là pagination partial.

**Cần sửa:** lưu riêng `pagination_complete`, `observed_reference_rows`, total unknown và metadata completeness. Đếm observed từ reference stores/receipts thật, không suy từ page limit/status. Thêm test partial không đủ 100, nhiều trang, và partial do metadata dù pagination đã đủ. Kiểm tra tái sinh từ report gốc: aggregator hiện chỉ giữ nguyên total đầu vào, không tự sửa historical `0` sai thành unknown; nếu archive còn mang `0 < kept`, guard sẽ dừng thay vì tái tạo CSV đã chỉnh.

### D. [Cao] Receipt verification bị diễn giải vượt phạm vi sang source corpus và cấu hình accelerator

**Vị trí:** `scripts/aggregate_data.py:49–73, 197–202, 469–481`; `run_metadata.json`; phần mở đầu README/index/Overview/Statistics/Performance và Methodology “Cryptographic Validation”.

`verify_report_archive()` chỉ so `receipt['archives']['report']` với `report.zip` và run ID. Trong metadata hiện tại, **201/201 đường dẫn đã ghi nhận đều kết thúc `report.zip`**; không có record corpus verification. Hàm hiện tại không đọc benchmark/environment bên trong corpus ZIP và không có corpus verifier tương đương.

`benchmark.json` hiện đã ghi CPU-only `true` ở 107/107 runs, và aggregator lấy `bench_data.get('cpu_only')` từ input. Do đó có thể báo **“retained run summaries record cpu_only=True for 107/107 runs”**. Không nên viết rằng so SHA-256 tự “confirms strictly CPU-only execution” hoặc tự xác nhận UI Hardware Accelerator=None. Hash chứng minh tính toàn vẹn so receipt; nội dung benchmark/environment mới là evidence về testbed.

**Cần bổ sung để đóng:** audit manifest phân biệt report/corpus archives, mỗi archive có run ID, hash/size, receipt, nội dung benchmark/environment liên quan và nguồn flags. Có thể dùng relative paths thay vì chỉ đường dẫn tuyệt đối của máy cũ. Nếu chưa cung cấp nguồn gốc để review lại, hạ giọng khẳng định theo phạm vi retained summaries; không kết luận các flags là sai hay đã bị bịa. Test kiểm tra JSON có `true` không thay thế kiểm chứng evidence đó.

### E. [Vừa] Authors 100% là chuỗi nhập cứng; audit metadata chưa đủ theo trường

**Vị trí:** `03_corpus_stats.ipynb`, cell Coverage and Metadata Audit, dòng chứa `100.0% present (20,000 / 20,000 verified)`; `scripts/aggregate_data.py:829–837`; `summary.json.metadata_field_audit`.

Summary chỉ đếm title, submission_date và metadata_source; `papers_detail.csv` không chứa authors/revised_dates/venue. Notebook hiển thị authors 100% bằng literal, không đọc metadata.json hay author counter. Không có bằng chứng audit có thể chạy lại cho kết luận này trong các file hiện có. `metadata_source` còn có default nên sự hiện diện của field đó không tự chứng minh provenance đúng.

`incomplete_references` đã được bổ sung và mean arXiv-reference completeness hiện là 1.0 trên 17.291 paper có pool/counter. Đây là cải thiện thật so với bản review cũ, nhưng là trung bình của counters trên **arXiv matching pool**, không chứng minh tất cả reference store hoặc pagination đều hoàn chỉnh. Ba partial paper vẫn có incomplete_references=0 là có thể hợp lệ: metadata của refs đã lấy đủ trong khi còn thiếu trang.

**Cần bổ sung:** xuất audit nhỏ từ corpus gốc, đếm được/thiếu/unknown theo title, authors, submission_date, revised_dates và các ref fields; ghi nullable và scope. Venue thiếu hợp lệ không tự là lỗi. Lưu mẫu nhiều thành viên/version/outcome với expected/observed, nguồn/ngày và sai lệch. Nếu chưa làm, hiển thị “not audited” thay cho literal authors 100%. Các non-null nội bộ đã được phân biệt với đề ở Overview; không cần nâng chúng thành yêu cầu môn học.

### F. [Cao] Ma trận handoff thêm các kết luận chưa có bằng chứng và có thể làm mất failure coverage

**Vị trí:** `03_corpus_stats.ipynb`, cell Failed Versions Audit Breakdown / Failure Disposition and Downstream Milestone 2 Handoff Matrix; đối chiếu `../src/crawling/download.py:479–530`.

Ma trận hiện ghi:

- 78 HTTP 404 đã được “Paced upstream recheck confirmed”; root cause là source không host/withdrawn; “marked no_tex if appropriate in M2”; “Zero parse impact”. Không có recheck log theo paper/version/date/endpoint trong retained audit. **HTTP 404 không đủ để xác nhận một valid no_tex outcome**; thiếu source vẫn ảnh hưởng version coverage/parsing.
- 30 case-collision đã “Preserved raw tar stream”, 4 lỗi khác đã “Retained corrupted byte sample”. Crawler hiện dùng `TemporaryDirectory` cho payload, chỉ publish khi status khác failed; khi rời context payload bị xóa. Chưa có inventory artifact chứng minh raw payload của các lỗi lịch sử đã được giữ riêng.
- M2 “will unpack with synthetic disambiguated filenames” và sanitized extraction đã scheduled. Đây chỉ có thể là phương án đề xuất nếu chưa có implementation/evidence/owner đi kèm; đổi tên TeX files còn phải giữ các liên kết `input/include` nhất quán.

**Cần sửa:** bảng tách **observed error / verified recheck / proposed action / current status / M2 impact**. Giữ failed status và danh sách 131 versions thuộc 115 papers cho đến khi có recovery evidence; không đổi 404 thành no_tex chỉ để bypass. Nếu đã recheck/giữ payload ở ngoài repo, gắn manifest/log xác định để người khác kiểm tra được. Không yêu cầu bỏ guard hay retry vô điều kiện.

### G. [Vừa] Giữ rõ phạm vi performance và hoàn tất public delivery

**Vị trí:** `04_performance.ipynb`, Multi-Run Benchmark Results / Analysis and Measurement Limits; `.github/workflows/deploy.yml`; `_config.yml`.

Các phân biệt đang đúng và nên giữ: cumulative machine-hours không phải thời gian hoàn thành của nhóm; 35,18 s/paper là post-discovery selected-record mean; 48,51 s/ID là phân bổ tổng run wall time, không phải latency của từng paper; mean RAM là mean không trọng số; global peak lấy summary thay vì trace đã thinned.

Đề yêu cầu runtime/memory của toàn hệ thống và đối chiếu disk với Colab. Cần làm rõ benchmark boundary, các chương trình/process được tính, cache mode và disk tracked paths; bổ sung capacity/free-space của testbed nếu muốn kết luận nằm trong giới hạn Colab. Final notebook export/backup đang bị loại khỏi measurement và đã công bố; nếu gọi số hiện tại là end-to-end bao gồm giao dữ liệu, phải đo thêm phần đó. Không biến “cold run” thành yêu cầu của đề: mixed cache chấp nhận được nếu công bố đúng.

Có workflow build/deploy và TOC M1 đúng. Lượt này [URL Pages](https://dangkhanh01.github.io/arXiv-report/) không truy cập được bằng web tool; chưa có cơ sở kết luận 404/private. Trước nộp cần xác nhận repo public, deploy đúng commit, mở Pages không đăng nhập, navigation/Plotly/MathJax hoạt động và links code/report đúng. Build local không thay thế kiểm tra publish hay render thực tế trong browser.

### H. [Cao, mới] Checkpoint mới có thêm expected versions nhưng aggregator giữ expected cũ

**Vị trí chính xác:** `scripts/aggregate_data.py:333–350` (nhánh merge không cập nhật `versions_expected`), `:498–504` (chỉ lấy max giữa expected đã giữ và số version rows quan sát).

**Đã tái hiện:** checkpoint đầu ghi expected=1 với v1 success; checkpoint sau ghi expected=3 nhưng mới có v1/v2 success, thiếu v3. Output lại là **versions_expected=2, versions_success=2, full_tex_papers=1, unresolved_source_papers=0**. Như vậy thiếu v3 bị che và paper được tính full-TeX sai. Test hiện có chỉ kiểm tra expected bị thiếu trong một archive, chưa kiểm tra expected tăng qua checkpoint.

**Cần sửa:** merge expected version history từ metadata/manifest có provenance; tối thiểu giữ expected lớn nhất hợp lệ giữa mọi input records và đối chiếu version labels thực tế. Không suy expected chỉ từ số rows đã thu được. Đây là lỗi đã chứng minh trên fixture, chưa khẳng định CSV hiện tại đã bị ảnh hưởng.

### I. [Cao, mới] Non-arXiv references có thể bị tính vào arXiv matching pool

**Vị trí chính xác:** `scripts/aggregate_data.py:235–237` (fallback sang `references_all.csv`), `:398–407` (cho phép ref ID rỗng, dùng title làm key), `:651` và `:675` (đếm toàn bộ references_dict như arXiv pool).

**Đã tái hiện:** fixture không có `references.csv`, có `references_all.csv` chứa đúng một reference “Non arxiv book”, `reference_arxiv_id` rỗng. Output vẫn **arxiv_reference_rows=1, papers_with_arxiv_pool=1**. `references_agg.csv` còn chứa ref ID rỗng, trái định nghĩa matching pool arXiv-keyed.

**Cần sửa:** tách all-reference store và arXiv pool; chỉ đưa reference có canonical arXiv ID vào pool/metric tương ứng. Không coi refs CSV rỗng (pool hợp lệ có thể rỗng) là lý do đưa mọi reference vào pool. Test cả pool rỗng hợp lệ và all-store chỉ có non-arXiv. Chưa khẳng định pool 366.416 hiện tại đã bị ảnh hưởng vì references_agg.csv không được commit.

### J. [Vừa, mới] Run ID bên trong manifest không được so với receipt/folder

**Vị trí chính xác:** `scripts/aggregate_data.py:49–64` chỉ kiểm tra receipt so với run ID lấy từ đường dẫn; `:232` đọc manifest, `:251` dùng papers của nó mà không so `manifest['run_id']` với run hiện tại.

**Đã tái hiện:** ZIP có manifest run_id=`WRONG-RUN`, receipt có run ID đúng folder và hash/size đúng ZIP đó. Aggregator vẫn chấp nhận paper vào output. Vì thế receipt kiểm tra đúng integrity không bảo đảm archive thuộc đúng logical run mà report đang gán.

**Cần sửa:** validate schema và so run identity giữa folder, receipt, manifest, benchmark nếu benchmark có field run ID. Thất bại phải dừng trước khi thay output. Không coi lỗi này là bằng chứng archive lịch sử đã bị tráo.

### K. [Cao, mới] Manifest hỏng/thiếu có thể bị bỏ qua và output vẫn được tạo

**Vị trí chính xác:** `scripts/aggregate_data.py:180–188` trả None nếu thiếu/parse lỗi JSON; `:251` thay manifest thiếu bằng `{}`; `:433–434` chỉ in lỗi rồi tiếp tục nếu đọc archive thất bại.

**Đã tái hiện:** thay manifest bằng `{broken` rồi cập nhật receipt hash/size hợp lệ. Aggregator vẫn trả thành công, lấy một paper từ CSV và tạo summary. Manifest không được validate như input bắt buộc. Integrity của ZIP không thay thế validation nội dung/schema.

**Cần sửa:** xác định required entries/schema cho report, dừng khi thiếu hoặc malformed; không biến lỗi đọc thành dữ liệu rỗng và tiếp tục báo corpus đầy đủ. Nếu có chế độ ingest một phần, phải khai báo riêng, báo coverage/error manifest và không ghi đè output hoàn chỉnh.

### L. [Cao, mới] Aggregation thất bại vẫn có thể ghi đè một phần bộ dữ liệu cũ

**Vị trí chính xác:** `scripts/aggregate_data.py:516–530` ghi `papers_unique.csv` trước khi kiểm tra invariant tại `:532–537`; các output tiếp theo cũng được ghi lần lượt trực tiếp vào target (`:539`, `:572`, `:612`, `:940`).

**Đã tái hiện:** target ban đầu có `papers_unique.csv` chứa sentinel; input có total=0, kept=1. Hàm ném ValueError đúng ở invariant, **nhưng papers_unique.csv cũ đã bị thay bằng dữ liệu mới**. Các file còn lại có thể vẫn là snapshot cũ; Book build sau đó có thể trộn nhiều lần aggregation.

**Cần sửa:** hoàn tất validation/tính toán trước, ghi trọn bộ outputs vào staging và chỉ publish snapshot khi mọi bước thành công. Thêm test lỗi invariant/parse đảm bảo toàn bộ target cũ được giữ nguyên. Test “bad receipt giữ summary cũ” hiện có không bao phủ lỗi xảy ra sau receipt verification.

### Tra cứu dòng chính xác cho các lỗi đã ghi ở lượt trước

Số dòng dưới đây là dòng vật lý của file tại report commit `4f06acf`; với `.ipynb` là dòng JSON source khi mở bằng text editor, không phải số cell/line hiển thị trong Jupyter. Source code/notebooks không bị thay đổi trong hai lượt review này.

| Phát hiện | Vị trí chính xác |
|:---|:---|
| A — Discovery coverage/missing/unexpected nhập cứng | `scripts/aggregate_data.py:780–783` |
| A — Fallback số đo size | `book/content/milestone1/03_corpus_stats.ipynb:157–160` |
| B — Nuốt lỗi corpus ZIP và fallback dung lượng/file count | `scripts/aggregate_data.py:893–896` |
| B — Notebook fallback “6.87 GiB” | `book/content/milestone1/04_performance.ipynb:115` |
| B — Nhãn khẳng định “Complete Merged Output on Filesystem” | `book/content/milestone1/04_performance.ipynb:129` |
| C — Cộng 100 refs/partial | `scripts/aggregate_data.py:660–664` |
| C — Fallback cộng 300 ở notebook | `book/content/milestone1/03_corpus_stats.ipynb:141` |
| C — Gọi confirmed non-arXiv là corpus-wide | `book/content/milestone1/04_performance.ipynb:405` |
| D — Verifier chỉ đọc receipt entry report | `scripts/aggregate_data.py:55` |
| D — CPU-only note khẳng định Hardware accelerator=None | `book/content/milestone1/04_performance.ipynb:130` |
| D — Overview gộp xác minh source/report và CPU-only | `book/content/milestone1/01_overview.md:8` |
| E — Authors 100% nhập cứng | `book/content/milestone1/03_corpus_stats.ipynb:683` |
| F — Recheck 404 / no_tex / zero parse impact | `book/content/milestone1/03_corpus_stats.ipynb:437–439` |
| F — Tuyên bố đã giữ raw tar và hứa đổi filenames M2 | `book/content/milestone1/03_corpus_stats.ipynb:445–446` |
| F — Tuyên bố đã giữ corrupt byte sample | `book/content/milestone1/03_corpus_stats.ipynb:466` |

## 4. Đối chiếu trực tiếp Report Requirements M1

| Yêu cầu | Hiện trạng | Hành động trước nộp |
|:---|:---|:---|
| Jupyter Book, repo riêng, GitHub Pages public | Có repo Git riêng, cấu hình và workflow | Xác nhận public/deploy/browser (G) |
| Bảng/hình sinh khi compile | Hai notebook execute=`force`, build lại thành công | Giữ; sửa số liệu/evidence đầu vào còn lỗi |
| Implementation, công cụ/API, quy trình | Có Overview/Methodology, module mapping, source policy | Giữ; sửa provenance và handoff quá mức (D/F) |
| Số paper thành công, success rate | Có 18.839 full-TeX, 19.885 resolved, 115 unresolved và version outcomes | Giữ định nghĩa riêng; không gọi no_tex là TeX success |
| Average paper bytes trước/sau bỏ figures | Có paired paper/version metrics và scope | Bỏ fallback, kiểm tra required fields (A) |
| Average references/paper và ref metadata success rate | Confirmed mean/success rate có denominator | Đếm observed thật, ghi đúng scope unknown/non-arXiv (C/E) |
| Per-paper/average/discovery time, end-to-end scope | Có thống kê và machine-hours | Giữ giới hạn, xác định boundary đầy đủ (G) |
| RAM max/mean, disk max/final output | RAM và tracked disk có số đo | Final corpus còn fallback; capacity/scope cần bổ sung (B/G) |
| Final benchmark trên Colab CPU-only | 107/107 retained flags `true` | Liên kết flags với nguồn environment/benchmark gốc (D) |

Metadata audit chi tiết, receipts và failure handoff là cách kiểm chứng độ tin cậy/hoàn chỉnh của các kết luận trong report, không phải tự bổ sung một rubric mới ngoài đề. Không cần nộp raw corpus trung gian để làm các audit nhỏ có thể review được.

## 5. Kiểm chứng đã thực hiện trong lượt này

1. `.venv/bin/python -m unittest discover -s tests -v`: **11/11 pass**.
2. `.venv/bin/jupyter-book build --all -W --keep-going book`: **exit 0, build succeeded**, cả hai notebook được thực thi lại. Lần chạy sandbox đầu bị chặn mở socket localhost của Jupyter; chạy lại với quyền mở kernel thành công. Log `/tmp/arxiv-qc-build.log` có hai thông báo transport TCP của IPKernelApp; không mô tả kết quả là “không có bất kỳ warning nào”.
3. CSV counters: 20.000 paper; 27.608 versions = 26.234 success + 1.243 no_tex + 131 failed; 19.963 reference success + 3 partial + 1 failed + 33 not_found. Histogram với cận inf và 37 unknown đếm đủ 20.000. Không có elapsed time thiếu/không dương trong 20.000 selected paper records.
4. Tự dựng expected ID set từ assignments và tháng biên đã lưu: đủ 20.000 ID, 0 missing/unexpected/wrong-member. Không kiểm chứng lại tháng biên upstream trong lượt này.
5. Đếm provenance: 107 runs, 201 report ZIP entries; không có corpus ZIP verification entry.
6. Dùng fixture của `ReceiptTests.archive()` và `aggregate_corpus()` với target tạm, không đụng `book/data/`: tái hiện 1 paper vẫn coverage=100% và corpus=7.381.815.495 bytes/360.917 files dù không có corpus ZIP.

7. Rà bổ sung theo yêu cầu chỉ rõ dòng: đã dùng fixtures ZIP có receipts hash/size hợp lệ để tái hiện riêng 5 lỗi H–L, target đều là thư mục tạm; không thay dữ liệu report.

**Giới hạn tests hiện tại:** năm `CorpusInvariantTests` chủ yếu đọc artifacts đã commit. Test histogram dựng lại phép tính riêng thay vì kiểm tra output notebook; test CPU/provenance chỉ assert các flags. Chưa có regression ngăn giả số đo khi corpus vắng, tính missing/unexpected IDs sai, cộng 100/partial hay tác động khi thiếu KPI. Bổ sung test theo các hành vi A–F; không chỉ thêm assertion các con số snapshot hiện có.

## 6. Thứ tự sửa đề nghị

1. Sửa ingestion/merge/validation và publish output an toàn (H–L); bỏ coverage/dung lượng/fallback giả và sửa selection/verification corpus (A/B).
2. Chỉnh tuyên bố provenance/CPU-only, authors audit và failure handoff theo evidence thật (D/E/F).
3. Đếm observed references từ stores, sửa phạm vi confirmed/observed và unknown (C).
4. Chạy lại aggregation từ input thật sang target tạm; đối chiếu output với bản hiện có, bổ sung regression; sau đó strict build.
5. Xác nhận Pages/browser và links nộp bài (G).

Chỉ đóng từng mục khi có sửa đổi và bằng chứng tương ứng. Không cần làm lại các sửa đổi đã đạt ở mục cũ 2, 3, 5, 6.

---

## Phụ lục — Nội dung review ban đầu ngày 31/10/2026 (lịch sử)

> **Chỉ để truy vết:** phần dưới giữ nguyên findings trước đợt sửa. “Chưa sửa”, “0/107 flags”, số dòng và các số liệu ở đây phản ánh snapshot cũ. Dùng bảng trạng thái ngày 01/11/2026 ở đầu file để biết mục nào còn mở. Phần tóm tắt đóng toàn bộ QC của bản trước đã được thay thế bằng đánh giá có kiểm chứng phía trên.

## Nội dung rà soát chi tiết và phương án đã thực hiện

## 1. Tổng references bằng 0 nhưng số arXiv references giữ lại lớn hơn 0

**Mức độ: cao — lỗi nhất quán dữ liệu, chưa giải quyết.**

### Vị trí

- `book/data/papers_detail.csv`, dòng **18345**, **18437**, **18464**.
- `book/data/summary.json`, dòng **27–33**: tổng references, số non-arXiv và các giá trị trung bình.
- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **129–138**, **163–167**, phần **Corpus Key Performance Indicators**: đọc và trình bày tổng/trung bình.
- Cùng notebook, dòng **446–470**, phần **Reference Mining & Citation Pool Breakdown**: donut và phân nhóm references.
- `scripts/aggregate_data.py`, dòng **289–296**: `safe_int` mặc định 0 khi thiếu bộ đếm; dòng **640–646**: cộng tổng và suy ra non-arXiv bằng hiệu.

### Bằng chứng

| Paper | Dòng CSV | reference_status | total_references | kept_references |
|---|---:|---|---:|---:|
| `2602.01405` | 18345 | partial | 0 | 77 |
| `2602.00562` | 18437 | partial | 0 | 8 |
| `2602.01397` | 18464 | partial | 0 | 78 |

Một tập con có 77/8/78 phần tử không thể thuộc một tập tổng có 0 phần tử nếu hai bộ đếm cùng phạm vi. Có thể tổng chưa xác định đã bị lưu là 0 hoặc hai bộ đếm đến từ các snapshot khác nhau; chưa có backup gốc để xác định nguyên nhân.

### Ảnh hưởng

- `734157` chưa đủ cơ sở để được gọi là tổng đầy đủ của mọi references đã thu thập.
- `36.70785 references/paper` là trung bình của bộ đếm hiện lưu, chưa phải trung bình đầy đủ được xác nhận.
- `367741 non-arXiv references` được tính bằng hiệu của các bộ đếm chưa nhất quán.
- Ba paper partial bị xếp như paper có 0 references, gây sai diễn giải phân phối.
- Không được tự đổi tổng của ba paper thành đúng bằng số kept: còn có thể có non-arXiv references hoặc trang chưa lấy được.

### Cách xử lý và điều kiện đóng

1. Đối chiếu `papers.csv`, manifest, reference stores và receipts của ba paper trong backup gốc.
2. Tách `unknown` khỏi số 0 thật; lưu rõ trạng thái pagination và phạm vi bộ đếm.
3. Nếu chỉ giữ được kết quả một phần, báo cáo là số quan sát được hoặc tổng chưa hoàn chỉnh, ghi số paper được đo.
4. Tính lại tổng, trung bình, donut và histogram trên phạm vi nhất quán.
5. Thêm kiểm tra `kept <= total` khi total đã xác định; không âm thầm thay unknown bằng 0.

## 2. Histogram references bỏ sót một paper

**Mức độ: vừa — lỗi biểu đồ xác nhận được, chưa sửa.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **465–470**, code cell trong **Reference Mining & Citation Pool Breakdown**.
- `book/data/papers_detail.csv`, dòng **10718**.

### Bằng chứng

```python
bins=[-1, 0, 10, 25, 50, 100, 1000]
```

Paper `2602.19887` có **1002 references**. Giá trị này nằm ngoài cận cuối; `pd.cut` biến thành giá trị thiếu, rồi `value_counts()` bỏ qua. Tổng histogram là **19999 paper**, trong khi tiêu đề ghi **20000**. Nhãn cuối `>100 refs` cũng không khớp cận trên hữu hạn 1000.

### Cách xử lý và điều kiện đóng

- Dùng cận cuối `float('inf')` hoặc `np.inf`.
- Tách nhóm unknown sau khi xử lý mục 1.
- Tính N từ số record thật được đưa vào biểu đồ.
- Kiểm tra tổng nhóm bằng tổng đối tượng thuộc phạm vi; thêm trường hợp trên 1000 vào kiểm tra hồi quy.

## 3. “Independent Runs” theo thành viên đếm sai phạm vi

**Mức độ: vừa — nhãn và phạm vi thống kê sai, chưa sửa.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **207–227**, phần **Team Member Partition Breakdown**, cột `Independent Runs`.
- `book/data/summary.json`, dòng **52–73**, `member_breakdown`.
- `scripts/aggregate_data.py`, dòng **721–735**: đếm run từ `papers_dict` đã deduplicate.
- `book/data/benchmark.json`, dòng **15** và mảng `runs` bắt đầu dòng **24**: 107 run benchmark.

### Bằng chứng

| Thành viên | Run từ record paper được chọn | Run trong benchmark |
|---|---:|---:|
| Danh | 18 | 35 |
| Khang | 21 | 29 |
| Khánh | 18 | 23 |
| Nguyên | 18 | 20 |
| Tổng | **75** | **107** |

Aggregator đang đếm các run ID còn gắn với paper sau gộp. Run retry hoặc run không còn record được chọn có thể biến mất khỏi phép đếm này. Đây không phải tổng số run đã thực hiện. Số 107 không tự mâu thuẫn với 75 nếu phạm vi được đặt tên đúng.

### Cách xử lý và điều kiện đóng

- Nếu giữ nhãn tổng run, đếm theo `benchmark['runs']` hoặc run metadata, với định nghĩa rõ checkpoint/final của cùng run.
- Nếu giữ phép đếm hiện tại, đổi tên thành “Runs represented by selected paper records” và trình bày số benchmark runs riêng.
- Tổng theo thành viên phải khớp tổng benchmark nếu cùng phạm vi.
- Cột `Completion Rate` ở dòng **215**, **225** chỉ đo số record ID/5000. Đổi thành `ID Record Coverage`; không hiểu nó là tỷ lệ tải đủ TeX.

## 4. Số dự phòng nhập cứng và discovery coverage cố định có thể che đầu vào thiếu

**Mức độ: vừa — lỗi độ tin cậy khi cập nhật dữ liệu, chưa sửa.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **116–153**, code cell KPI.
- Cùng notebook, dòng **156**: in `100.0%` cố định.
- Cùng notebook, dòng **446–448**: tổng references dự phòng nhập cứng.
- `scripts/aggregate_data.py`, dòng **740**: `id_discovery_coverage = 1.0`.

### Bằng chứng

```python
summary.get('full_tex_papers', 18839)
summary.get('reference_api_success_rate', 0.998)
summary.get('arxiv_reference_rows', 366416)
```

Hiện JSON có các trường này nên không đủ căn cứ kết luận mọi KPI hiện sai. Lỗi là khi trường bị mất, Book có thể dùng số lịch sử hoặc 0 và vẫn build thành công. Tỷ lệ discovery 100% cũng chưa được tính từ tập ID được giao.

### Cách xử lý và điều kiện đóng

- Với trường bắt buộc: kiểm tra schema rồi dừng khi thiếu.
- Với số tính được từ CSV: tính lại hoặc đối chiếu CSV với summary.
- Discovery coverage: so sánh tập ID được giao với tập ID có metadata hợp lệ; báo cáo missing/unexpected IDs, không chỉ đếm số dòng.
- Dữ liệu hiện tại có 20000 ID và các dải quan sát phù hợp phân công; mục này không khẳng định đang thiếu ID.
- Thêm trường hợp JSON thiếu trường và corpus thiếu ID vào kiểm tra.

## 5. Diễn giải lỗi case collision suy ra Windows không có bằng chứng

**Mức độ: thấp — diễn giải sai nguyên nhân.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **403**, hàm `categorize_error`, phần **Failed Versions Audit Breakdown**.
- Đối chiếu source crawler: `src/crawling/download.py`, dòng **181–183** trong repository code `arXivProject`, kiểm tra bằng `casefold()`.

### Bằng chứng và ảnh hưởng

Nhãn hiện tại là `Case Collision Guard (Windows case-insensitive filesystem collision)`. Kiểm tra `casefold()` được chạy độc lập với hệ điều hành. Có **30 version** mang lỗi `Case-colliding archive paths.`; lỗi không chứng minh các run chạy Windows.

### Cách xử lý và điều kiện đóng

Đổi nhãn thành “Archive paths collide under case-insensitive normalization”. Chỉ nêu hệ điều hành nếu có metadata của chính run. Không tự bỏ guard để tăng tỷ lệ thành công.

## 6. Methodology gọi pagination là cursor trong khi implementation dùng offset

**Mức độ: thấp — thuật ngữ implementation chưa đúng.**

### Vị trí

- `book/content/milestone1/02_methodology.md`, dòng **48**, mục **Complete Pagination**.
- Source crawler `src/crawling/references.py`, dòng **56**, **214**, **238–249** trong repository code.

### Bằng chứng

Báo cáo ghi “cursor-based next token”. Code gửi `offset`, kiểm tra `next` là số nguyên tăng dần rồi dùng làm offset tiếp theo.

### Cách xử lý và điều kiện đóng

Mô tả “offset-based pagination using the returned next offset”. Giải thích dừng khi không còn `next`; trang lỗi/offset không hợp lệ tạo kết quả partial. Đây là sửa mô tả, không phải bằng chứng crawler không paginate.

## 7. Chưa có đủ bằng chứng benchmark Colab CPU-only

**Mức độ: cao — yêu cầu benchmark chưa được chứng minh.**

### Vị trí

- `book/data/benchmark.json`, dòng **2–4**: environment Colab nhưng `cpu_only: null`, cache mode unknown.
- Cùng file, dòng **24** trở đi: các run lịch sử thiếu accelerator/cache flags.
- `book/content/milestone1/04_performance.ipynb`, dòng **126**, **144–151**, **349**, phần **Multi-Run Benchmark Results** và **RAM and cache**.

### Bằng chứng và ảnh hưởng

Có 107 run; **0/107 run có trường CPU-only được ghi rõ trong retained run summaries**. Environment string chứa Colab không chứng minh accelerator là None. Báo cáo đã nêu đúng giới hạn; yêu cầu testbed chưa vì thế được hoàn thành.

### Cách xử lý và điều kiện đóng

1. Tìm `benchmark.json` và environment metadata trong report ZIP gốc, gắn đúng run ID.
2. Không điền `true` suy đoán cho lịch sử.
3. Nếu không phục hồi được: chạy benchmark mới trên Colab với Hardware accelerator=None, lưu environment, cấu hình, commit, cache mode, scope ID, timing/RAM/disk và backup receipts.
4. Nêu rõ phạm vi benchmark mới; không dùng nó chứng nhận ngược 107 run cũ.
5. CPU-only là yêu cầu của đề; “cold” là đặc tính phép đo cần khai báo, không tự biến thành yêu cầu bắt buộc của đề.

## 8. Provenance của bảng lịch sử chưa đối chiếu ZIP/receipt gốc

**Mức độ: cao — bằng chứng nguồn số liệu chưa đầy đủ.**

### Vị trí

- `book/content/milestone1/02_methodology.md`, dòng **145**, mục **Cryptographic Validation**.
- `book/data/run_metadata.json`, từ dòng **2**, các record lịch sử có `sha256` nhưng không có `verified_archives`.
- `book/content/milestone1/04_performance.ipynb`, dòng **144–148**, bảng evidence.
- `scripts/aggregate_data.py`, hàm `verify_report_archive`, dòng **49–70**; kiểm tra đầu vào dòng **197–202**; xuất evidence dòng **474–475**.

### Bằng chứng và ảnh hưởng

**0/107 record lịch sử có `verified_archives`**. Một hash được lưu riêng không chứng minh đã so với receipt và archive thật. Cơ chế kiểm tra mới không xác minh ngược bộ CSV hiện có.

### Cách xử lý và điều kiện đóng

- Thu hồi nguyên cây backup các thành viên/tài khoản, giữ checkpoint, final backup và `backup_receipt.json` liền kề ZIP.
- Chạy lại aggregator trên đầu vào thật; xác minh run ID, filename, byte count và SHA-256 trước khi dùng số liệu.
- Kiểm tra report ZIP và corpus ZIP theo đúng phạm vi: aggregator hiện xác minh report ZIP, không tự chứng nhận corpus ZIP.
- Giữ danh sách archive được chọn, bằng chứng receipt và quyết định deduplicate; build lại số liệu.
- Hash/receipt chỉ kiểm tra integrity, không chứng minh metadata và source có nội dung đúng.

## 9. Chưa đo dung lượng corpus cuối đầy đủ

**Mức độ: cao — thiếu số đo output theo yêu cầu.**

### Vị trí

- `book/data/benchmark.json`, dòng **11–13**, **21–22**.
- `book/content/milestone1/04_performance.ipynb`, dòng **123–125**, phần **Storage Footprint**; dòng **354**, phần **Storage**.

### Bằng chứng

- `merged_corpus_tex_bib_bytes = 5424427008` (~5.05 GiB): tổng byte counters của `.tex/.bib` theo unique versions.
- `sum_run_final_disk_bytes = 23259066601` (~21.66 GiB): tổng disk cuối các run, có thể trùng và gồm work files.
- Bảng hiện ghi “Complete Merged Output on Filesystem: Not measured”.

Không giá trị nào là phép đo trực tiếp một corpus cuối gồm sources, metadata, reference stores, receipts và manifest.

### Cách xử lý và điều kiện đóng

1. Phục hồi, xác minh và hợp nhất đủ phạm vi dữ liệu; không cộng lại các checkpoint trùng.
2. Đo cây corpus cuối, ngoài ZIP backup/cache/staging/output M2.
3. Lưu bytes, file count, paper/version coverage, ngày đo và định nghĩa phạm vi. Trên Colab/Linux có thể dùng `du -sb <corpus>` cho logical bytes và `du -sB1 <corpus>` cho allocated bytes.
4. Ghi rõ metric nào là logical/allocated. Nếu corpus còn thiếu, kèm coverage và không gọi là toàn bộ corpus đã hoàn tất.
5. Peak tracked disk của run và dung lượng output cuối là hai phép đo khác nhau; giữ riêng.

## 10. Field-level metadata completeness và đối chiếu mẫu còn thiếu

**Mức độ: vừa — thiếu bằng chứng chất lượng dữ liệu.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **599–610**, phần **Coverage and Metadata Audit**.
- `book/data/summary.json`, dòng **34–35**: completeness hiện `null`, denominator=0.
- `book/data/papers_detail.csv`, dòng **1**: không có authors, revised_dates, venue hoặc incomplete_references.
- `book/content/milestone1/01_overview.md`, dòng **39–59**, schema và internal validation rules.

### Bằng chứng và giới hạn

Audit hiện kiểm tra ID trùng, version count, title/submission_date rỗng. Nó chưa xác nhận author lists, revision dates, venue, reference title/authors/v1 date/S2 ID. File `references_agg.csv` không được commit; điều này không tự là lỗi, nhưng cần bảng audit nhỏ thay thế.

Các trường bổ sung non-null trong Overview là quy tắc nội bộ của nhóm; đề chỉ đánh dấu non-null rõ cho các khóa ID. Không coi venue thiếu là lỗi nếu venue nullable. Không tuyên bố metadata đầy đủ 100% khi chưa có số đo.

### Cách xử lý và điều kiện đóng

- Xuất bảng audit nhỏ từ corpus/backup: số được kiểm tra, số thiếu theo trường, unknown và provenance date resolution.
- Completeness của arXiv matching pool phải tách với toàn bộ reference store và pagination completeness.
- Lập mẫu gồm nhiều thành viên, paper nhiều version, no_tex, reference partial và ID kiểu cũ nếu có.
- Lưu expected/observed, nguồn đối chiếu, ngày kiểm tra, sai lệch và hành động xử lý. Hai mẫu date đã đối chiếu trong lượt review không thay thế audit này.

## 11. 131 version lỗi chưa có quyết định xử lý theo nhóm

**Mức độ: vừa — cần bổ sung phân tích/handoff, không đồng nghĩa mọi failure là lỗi implementation.**

### Vị trí

- `book/content/milestone1/03_corpus_stats.ipynb`, dòng **386–416**, phần **Failed Versions Audit Breakdown**.
- `book/content/milestone1/04_performance.ipynb`, phần **Downstream Corpus Readiness and Handoff**, hàng `Unresolved source papers`.
- `book/data/versions.csv`, các record status=failed; `book/data/summary.json`, dòng **8**, **14**.

### Bằng chứng

| Lỗi được lưu | Version |
|---|---:|
| Source HTTP 404 | 78 |
| Case-colliding archive paths | 30 |
| Unsafe archive path | 16 |
| Source transport stream failed | 3 |
| Unrecognized or damaged source | 2 |
| Tar member exceeds byte limit | 2 |
| Tổng | **131** |

131 version lỗi thuộc **115 paper**. Có phân loại và ví dụ, nhưng chưa có quyết định sửa/retry/chấp nhận thiếu theo nhóm và kết quả recheck.

### Cách xử lý và điều kiện đóng

- Thêm bảng observed error → hướng kiểm tra → trạng thái cuối → ảnh hưởng M2.
- 404 không chứng minh PDF-only/no_tex. Kiểm tra lại đúng version/endpoint nếu nhóm quyết định recheck.
- Transport failures có thể retry theo policy; archive safety/size failures cần kiểm tra payload và giới hạn. Không bỏ guard hoặc tăng giới hạn vô điều kiện để làm đẹp tỷ lệ.
- Lưu danh sách còn thiếu và evidence; không nâng chúng thành success nếu chưa phục hồi được source.
- `no_tex` hợp lệ được giữ record rỗng theo đề, không cộng vào TeX success và không coi là lỗi tải.

## 12. GitHub Pages và bản public chưa được xác nhận

**Mức độ: cần kiểm tra trước nộp — trạng thái chưa xác minh, không kết luận site hỏng.**

### Vị trí

- `book/_config.yml`, mục `repository`, URL repo `https://github.com/Dangkhanh01/arXiv-report`.
- `.github/workflows/deploy.yml`, bước Build và Deploy GitHub Pages.
- `README.md`, phần **Automated GitHub Pages Deployment**.

### Bằng chứng và cách xử lý

Có repository Git riêng và workflow deploy. Công cụ duyệt web trong lượt review không truy cập được `https://dangkhanh01.github.io/arXiv-report/`; không đủ căn cứ suy ra lỗi 404 hoặc site private.

Trước nộp cần xác nhận repo public, deployment thành công đúng commit, URL Pages mở ở chế độ không đăng nhập, navigation và cả hai notebook hiển thị đủ bảng/Plotly charts. Build local không tự xác nhận trạng thái publish. Kiểm tra links code/report gửi Moodle trỏ đúng bản cuối.

## 13. Giới hạn số đo cần giữ rõ trong báo cáo

**Mức độ: cải thiện/giới hạn phép đo, không phải mọi mục là lỗi số học hiện tại.**

- `04_performance.ipynb`, dòng **77**: final notebook export/backup nằm ngoài benchmark, checkpoint trong pipeline được tính. Giữ định nghĩa này nhất quán; nếu gọi phép đo bao trùm toàn bộ quy trình giao dữ liệu thì cần đo thêm phần bị loại.
- Cùng notebook, dòng **119**: ~48.51 s/ID là tổng recorded run wall time chia unique IDs; ~35.18 s/paper là mean post-discovery của selected records. Không đồng nhất hai số hoặc gọi số phân bổ là latency từng paper.
- Cùng notebook, dòng **121**: RAM mean hiện là trung bình không trọng số của mean từng run. Nhãn đang nói đúng. Nếu cần trung bình theo thời gian toàn bộ benchmark, dùng raw samples với khoảng thời gian tương ứng hoặc duration-weighted estimate và ghi giả định.
- Cùng notebook, dòng **120**, phần **Resource Footprint Over Time**: global peak từ run summaries, trace đã thinned. Không lấy peak của trace đã lấy thưa làm global peak; sampling có thể bỏ lỡ spike.
- Cùng notebook, dòng **122**, **354**: tracked disk không tự là toàn bộ disk của VM. Cần runtime capacity và phạm vi thư mục để so với giới hạn Colab.

## 14. Kiểm chứng đã làm và phần tests chưa bao phủ

### Những điểm hiện đạt trong phạm vi offline

- Jupyter Book build `--all -W --keep-going` đã thành công; hai notebook được thực thi. Cấu hình execution hiện là `force`.
- Sáu test receipt/aggregation pass, gồm receipt sai/thiếu, checkpoint cũ sai receipt, completeness chưa biết và version expected chưa có record.
- Không có paper ID trùng hoặc `(paper, version)` trùng trong CSV hiện tại.
- Version labels liên tiếp từ 1 đến N trong các record hiện có.
- 20000 paper, 27608 version; 26234 success + 1243 no_tex + 131 failed khớp tổng.
- 18839 paper full-TeX, 19885 paper resolved source outcomes, 115 paper unresolved khớp bảng version.
- 19963 reference success, 3 partial, 1 failed, 33 not_found khớp 20000; partial không được tính success.
- Số references trung bình đã có trong bảng KPI, nhưng ý nghĩa bị giới hạn bởi lỗi bộ đếm ở mục 1.

### Không được suy ra từ các kiểm tra này

Tests hiện chưa bảo vệ đầy đủ các trường hợp: kept>total, unknown tổng references, histogram >1000, số run theo thành viên, JSON thiếu KPI bắt buộc, expected ID coverage, field-level metadata và trạng thái site public. Nên bổ sung kiểm tra các bất biến này khi sửa lỗi tương ứng; không chỉ kiểm tra code chạy không exception.

Build pass không xác minh lại ZIP lịch sử, không thay benchmark Colab, không chứng minh source byte-exact hoặc metadata đúng với upstream.

## Thứ tự xử lý

1. **Số liệu references không nhất quán** (mục 1), rồi tính lại mọi bảng/hình phụ thuộc.
2. **Histogram, run counts, fallbacks/coverage** (mục 2–4).
3. **Bằng chứng CPU-only, archive receipts và dung lượng corpus cuối** (mục 7–9).
4. **Metadata audit, xử lý failures, thuật ngữ và giới hạn phép đo** (mục 5–6, 10–11, 13).
5. **Public deployment và links nộp bài** (mục 12).

Chỉ đóng một mục khi có sửa đổi hoặc bằng chứng tương ứng. Ghi “chưa xác minh” giúp báo cáo trung thực, nhưng không đồng nghĩa yêu cầu đó đã hoàn thành.

</details>
