# Rà soát chất lượng report Milestone 1

Ngày rà soát: **31/10/2026**. Phạm vi: bản report hiện tại trong repository `arXiv-report`, dữ liệu đã lưu trong `book/data/`, notebook sinh báo cáo, aggregator và các phép kiểm tra offline. Nội dung này thay toàn bộ review cũ.

**Kết luận:** Báo cáo có đủ khung nội dung chính, nhưng chưa thể kết luận chỉ còn ba thiếu sót về benchmark/backup/disk. Vẫn có lỗi thống kê và diễn giải bên dưới. Build thành công hoặc tests pass không xác nhận dữ liệu lịch sử là đúng.

Số dòng trong `.ipynb` là dòng JSON của file nguồn, không phải dòng Python trong một cell. Mỗi mục ghi thêm tên phần/cell để tìm khi mở bằng Jupyter. Các vị trí áp dụng cho bản được rà soát; sau khi sửa cần cập nhật lại.

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
