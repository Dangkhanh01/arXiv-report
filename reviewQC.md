Được. Mình sẽ chỉ rõ **vị trí → bằng chứng → vì sao có vấn đề → sửa ở đâu và sửa thế nào**. Có vài điểm cần phân biệt: **số liệu sai**, **nhãn gây hiểu nhầm**, và **đề xuất nâng chất lượng** không có mức độ nghiêm trọng giống nhau.

Các vị trí dưới đây theo bản hiện tại. Với notebook, mình đếm **cell từ 1, gồm cả Markdown và code**; số dòng trong liên kết là dòng của file `.ipynb` khi mở dưới dạng text.

**1. Tuyên bố hoàn tất corpus và chỉ số “All Versions TeX”**

**Vị trí trong báo cáo:**

- [Overview, dòng 8](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/01_overview.md:8): câu “completely harvested, validated…”.
- [Statistics, cell 3, dòng 94](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/03_corpus_stats.ipynb:94): định nghĩa `full_source_papers` là paper có TeX ở mọi version.
- Cùng notebook, cell 4, dòng 260: nhãn bảng **“Full Source Papers (All Versions TeX)”**.

**Bằng chứng lỗi:** [Aggregator, dòng 518](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:518) đếm paper thành công khi:

```python
versions_success + versions_no_tex >= versions_expected
```

Điều này bao gồm paper có version **không có TeX**, trái với định nghĩa và nhãn trên báo cáo.

Tính từ bảng version hiện tại:

| Điều đang đo | Kết quả |
|---|---:|
| Paper có record | 20.000 |
| Paper mọi version đều `success` | **18.839** |
| Paper mọi version thuộc `success` hoặc `no_tex` | **19.885** |
| `full_source_papers` báo cáo đang ghi | **19.874** |

Số **19.885** mình tính thêm trong lần kiểm tra này cho thấy **chỉ đổi tên 19.874 cũng chưa đủ**.

Có ví dụ cụ thể: bài `2606.17012` vẫn ghi một version lỗi ở [bảng paper, dòng 306](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/papers_detail.csv:306), nhưng version đó đã thành `no_tex` ở [bảng version, dòng 922](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/versions.csv:922). Hai bảng đang giữ kết quả từ những lần chạy khác nhau.

**Vì sao ảnh hưởng điểm:** người chấm không biết “100% hoàn tất” nghĩa là đã tìm thấy ID, đã có record hay đã tải đủ TeX. Đây là sự khác nhau trực tiếp liên quan yêu cầu crawl mọi version.

**Cách sửa tốt hơn:**

- Gộp kết quả từng version trước.
- Tính lại trạng thái paper từ tập version đã gộp.
- Tách ba chỉ số: **ID discovery coverage**, **full-TeX paper rate**, **resolved source-outcome rate**.
- Ở Overview, thay tuyên bố hoàn tất tuyệt đối bằng số lượng và trạng thái còn lại.

Một câu có thể dùng:

> Metadata was resolved for all 20,000 assigned IDs. Among 27,608 version records, 26,234 contain TeX sources, 1,243 are recorded as `no_tex`, and 131 remain failed.

Giữ `no_tex` là đúng đề; **đếm nó thành “All Versions TeX” mới là sai**.

---

**2. Tỷ lệ thành công crawl references đang đo sự hiện diện của pool**

**Vị trí:**

- [Statistics, cell 4, dòng 266](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/03_corpus_stats.ipynb:266): dòng KPI **“Reference Extraction Success Rate”**.
- [Aggregator, dòng 536](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:536): đếm số paper xuất hiện trong `references_dict`.
- Cùng script, dòng 598: lấy số đó làm `reference_jobs_success`; dòng 600: phần còn lại thành `reference_jobs_failed`.

**Bằng chứng:**

| Trạng thái | `summary.json` | Đếm từ `papers_detail.csv` |
|---|---:|---:|
| success | 17.291 | 19.302 |
| failed | 2.709 | 655 |
| not_found | 0 | 34 |
| partial | 0 | 9 |

**Vì sao có vấn đề:** lấy được response thành công và có ít nhất một reference trong pool là hai sự kiện khác nhau.

Ví dụ: API trả thành công, paper có 24 references nhưng tất cả ngoài arXiv. Job crawl có thể thành công, còn pool matching arXiv rỗng. Không thể từ pool rỗng suy ra job thất bại.

**Điểm cần nói công bằng:** **86,455% không nhất thiết vô dụng hay sai phép chia.** Nó có thể mô tả tỷ lệ paper có reference trong pool. Nhưng phải đặt tên đúng, chẳng hạn **“Papers with a non-empty arXiv reference pool”**; không được dùng nó để ghi phần còn lại là API failure.

**Cách sửa:**

- Đếm job theo `reference_status` sau khi giải quyết các lần retry.
- Báo cáo riêng `success`, `partial`, `failed`, `not_found`.
- Giữ thêm chỉ số paper có pool arXiv nếu cần.
- Quy định rõ API trả thành công nhưng danh sách rỗng được tính thế nào.

Đề yêu cầu tỷ lệ thành công crawl reference metadata ở [dòng 351](C:/Users/ADMIN/Desktop/Do_an/arXivProject/ARXIV_PROJECT_FULL.md:351), nên đây là phần cần làm rõ để đáp ứng yêu cầu, không chỉ là lựa chọn trình bày.

---

**3. Biểu đồ “mọi references” thực chất đang dựa chủ yếu trên references đã lọc**

**Vị trí:**

- [Statistics, cell 12, dòng 1051](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/03_corpus_stats.ipynb:1051): lấy số arXiv/non-arXiv để vẽ donut.
- [Methodology, dòng 50](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/02_methodology.md:50): nói `references_all.json` giữ mọi reference.
- [Aggregator, dòng 204](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:204): đọc `references.csv`; chỉ khi không có dòng mới đọc `references_all.csv`.

**Vì sao sai về phương pháp:** bạn muốn đo “trong mọi references có bao nhiêu phần trăm ngoài arXiv”, nhưng lại ưu tiên đầu vào đã lọc arXiv. Sau bước lọc, non-arXiv bằng 0 không chứng minh dữ liệu gốc không có non-arXiv.

Đây giống như lọc chỉ sinh viên đậu rồi dùng tập đó kết luận tỷ lệ rớt bằng 0.

**Hệ quả hiện tại:**

- Nhãn **366.416 “Total Extracted References”** chưa phản ánh đúng phạm vi.
- **18,32 references/paper** chưa thể gọi là trung bình mọi references crawl được.
- Donut non-arXiv bằng 0 chưa có sức thuyết phục.
- [Dòng 611 của aggregator](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:611) còn gán `average_reference_completeness_rate = 1.0` cố định.

**Cách sửa:**

- Đọc dữ liệu “all references” để thống kê toàn bộ.
- Đọc pool đã lọc riêng để thống kê đầu vào matching.
- Giữ trạng thái pagination và các bộ đếm metadata thiếu.
- Tính completeness thật, hoặc bỏ chỉ số nếu thiếu bằng chứng.

Không nhất thiết đưa CSV references rất lớn lên GitHub. Có thể xuất một bảng nhỏ theo paper gồm `total_references`, `arxiv_references`, `non_arxiv_references`, trạng thái và pagination để build biểu đồ.

Yêu cầu giữ mọi references local có ở [đề, dòng 321](C:/Users/ADMIN/Desktop/Do_an/arXivProject/ARXIV_PROJECT_FULL.md:321). Nhưng lỗi mình đang chỉ ra là **thống kê chưa chứng minh được việc đó**, chưa đủ căn cứ kết luận crawler đã làm mất dữ liệu.

---

**4. So sánh kích thước trước/sau lọc trên hai tập khác nhau**

**Vị trí:**

- [Statistics, cell 4, dòng 267](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/03_corpus_stats.ipynb:267): các hàng mean size trước/sau.
- Cell 8, dòng 565: biểu đồ cột dùng những mean này.
- [Aggregator, dòng 539](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:539): lọc các giá trị trước và sau thành hai danh sách độc lập.

**Bằng chứng:**

| Cấp thống kê | Mẫu trước lọc | Mẫu sau lọc |
|---|---:|---:|
| Version | 27.477 | 26.234 |
| Paper | 19.962 | 18.946 |

Nguyên nhân là script giữ giá trị `> 0`. `no_tex` có `after = 0` nên bị loại khỏi mean sau lọc nhưng vẫn có thể nằm trong mean trước lọc.

**Vì sao ảnh hưởng kết luận:** hai cột cạnh nhau khiến người đọc hiểu rằng cùng một tập paper được đo trước và sau. Thực tế, tập sau đã loại một nhóm đối tượng.

**Cách sửa tốt hơn:**

- Ghép cặp `before` và `after` theo cùng version.
- Quy định rõ `0` hợp lệ của `no_tex` khác với giá trị chưa biết do tải lỗi.
- Với paper, nói rõ có yêu cầu đủ số đo mọi version không.
- Nếu muốn phân tích riêng những version có TeX, dùng cùng tập đó cho cả trước và sau.

Ngoài ra, dòng 271 đang gọi tỷ lệ giảm dung lượng là **“100% figure & image exclusion efficiency”**. Hai chỉ số không tương đương: giảm dung lượng không đo trực tiếp bao nhiêu file hình đã bị loại.

**Mình không kết luận 95,74% tính trên tổng byte chắc chắn sai.** Lỗi đã xác nhận là các mean và mẫu số trình bày không khớp; cách diễn giải phần giảm cũng quá rộng.

---

**5. Benchmark checkpoint và timeline nhiều run bị tổng hợp sai**

**Vị trí:**

- [Aggregator, dòng 397](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:397): `if bench_data and not run_bench_entry`.
- [Performance, cell 8, dòng 570](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/04_performance.ipynb:570): vẽ toàn bộ samples bằng `elapsed_seconds`, không chia `run_id`.

**Lỗi chọn snapshot:** điều kiện trên chỉ giữ benchmark đầu tiên đọc được trong run.

Ví dụ run `77b8205a-…`:

- [Run metadata, dòng 309](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/run_metadata.json:309): có **24 ZIP checkpoint**, tổng hợp được **941 paper mới**.
- [Benchmark, dòng 464](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/benchmark.json:464): vẫn giữ bản đầu với `total_papers = 40`.

941 và 40 không nhất thiết phải bằng nhau trong mọi định nghĩa, nhưng ở đây code cho thấy rõ benchmark được lấy từ phần đầu, trong khi corpus được gom từ nhiều checkpoint phía sau.

**Lỗi timeline:** `elapsed_seconds` bắt đầu lại ở mỗi run. [CSV, dòng 140](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/resource_samples.csv:140) đang ở khoảng **6.296,86 giây**, dòng kế tiếp sang run khác quay về **79,93 giây**. Toàn file có 198 lần giảm như vậy.

Nối chúng thành một đường là nối hai đồng hồ khác nhau. **Chỉ sort toàn bộ theo `elapsed_seconds` cũng không sửa được**, vì vẫn trộn những phiên độc lập.

**Cách sửa:**

- Run hoàn tất: dùng benchmark cuối đã xác minh.
- Run bị ngắt: dùng prefix cuối có bằng chứng, ghi rõ chưa hoàn tất.
- Samples checkpoint lặp lại: loại phần trùng trước khi tổng hợp.
- Vẽ từng run riêng hoặc thêm bộ chọn run.
- RAM mean: nếu là trung bình các mean của run, đặt tên đúng như vậy; nếu muốn trung bình theo thời gian, tính theo thời lượng quan sát.

Yêu cầu của đề là số đo kiểm chứng được. Đường timeline hiện tại không giúp kiểm chứng diễn biến của một phiên chạy thật.

---

**6. Kết luận performance có số sai và bằng chứng bị thay bằng giá trị cố định**

**Vị trí chính:** [Performance, cell 9, dòng 625](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/04_performance.ipynb:625).

Có bốn phần cần sửa:

| Đoạn hiện tại | Vấn đề | Sửa tốt hơn |
|---|---|---|
| CPU `<15%`, không thermal throttling | Telemetry đang dùng chỉ có thời gian, RAM, disk | Bỏ con số và kết luận nhiệt; hoặc bổ sung phép đo CPU thật |
| Dòng 628: RAM luôn dưới `350 MiB` | [Benchmark dòng 8](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/benchmark.json:8) ghi **581,08 MiB** | Sinh câu diễn giải từ dữ liệu, không nhập tay |
| “completely eliminating” nguy cơ OOM | Peak đã quan sát không bảo đảm mọi lần chạy tương lai | Giới hạn kết luận trong các lần chạy đã đo |
| Dòng 210: `Final Persisted Corpus Size` | Aggregator cộng disk cuối của các run | Đo corpus cuối đã hợp nhất hoặc đổi nhãn đúng phạm vi |

Về disk, tổng `.tex/.bib` từ bảng version khoảng **5,05 GiB**, còn `final_disk_bytes` tổng hợp khoảng **21,65 GiB**. [Aggregator, dòng 653](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/scripts/aggregate_data.py:653) đang cộng `final_disk_bytes` của từng run. Nó có thể chứa phạm vi khác nhau hoặc dữ liệu trùng, nên không tự động là dung lượng corpus cuối.

Cùng script, dòng 645 và 646 tự đặt:

```python
"cpu_only": True,
"cache_mode": "cold",
```

Trong khi bảng version có 1.259 dòng `used_cache=True`.

**Cách sửa:** giữ provenance thật của từng run; định nghĩa “cold” áp dụng cho thành phần nào; thiếu bằng chứng thì ghi chưa xác định. Sự xuất hiện cache không chứng minh dùng GPU, nhưng đủ để yêu cầu giải thích nhãn “cold”.

Một câu RAM chặt chẽ hơn:

> The run summaries report a maximum observed RSS of 581.1 MiB. Sampling may miss short-lived peaks.

---

**7. Methodology mô tả không khớp code đang có**

**Vị trí:** [Methodology, dòng 106](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/02_methodology.md:106), bảng “Software Module Mapping”.

| Báo cáo đang ghi | Code hiện tại |
|---|---|
| `discovery.py::OaiClient` | [discover.py:216](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/discover.py:216) |
| `sources.py::SourceExtractor` | [download.py:456 — download_version](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/download.py:456) |
| `references.py::S2Client` | [references.py:192 — collect_references](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/references.py:192) |
| `telemetry.py::ResourceSampler` | [metrics.py:59 — collect_resource_samples](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/metrics.py:59) |
| `CheckpointManager` | [checkpoints.py:84 — BackgroundCheckpoints](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/checkpoints.py:84) |

**Vì sao nghiêm trọng:** nếu giảng viên yêu cầu mở `SourceExtractor` để giải thích mà nhóm không tìm thấy, uy tín của cả methodology giảm ngay. Đây không phải nhận xét chủ quan về văn phong.

Nếu bảng nói về code của commit cũ thì phải gắn commit đó; nếu là tên khối kiến trúc minh họa thì phải ghi rõ, không trình bày như tên implementation.

Những vị trí khác trong cùng chương:

- **Dòng 34** nói chỉ giữ `.tex/.bib`, nhưng **dòng 95** thêm `.bbl/.sty/.cls`; Statistics cell 7, dòng 415 cũng thêm ba loại này. Code hiện giữ `.tex/.bib`.
- **Dòng 91–92:** S2 delay 1 giây, 5 attempts, cap 60 giây. [Notebook crawler, dòng 228](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/notebooks/milestone1.ipynb:228) hiện đặt 3 attempts, S2 3,1 giây, cap 120 giây. Cần lấy cấu hình từ run thực tế, không mặc định cấu hình hiện tại là cấu hình lịch sử.
- **Dòng 114:** “at most 39” paper phải crawl lại. Checkpoint đang chờ upload/commit cũng có thể chưa được bảo vệ. Nên viết: dữ liệu chỉ được bảo vệ sau khi receipt và trạng thái checkpoint đã commit.
- [README, dòng 65](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/README.md:65) nói aggregator kiểm SHA-256. Trong script hiện tại, `sha256_file()` mới được định nghĩa, chưa được gọi. Hoặc thực hiện kiểm tra, hoặc bỏ tuyên bố này.

---

**8. Thiếu discovery time trong bảng và gọi sai phạm vi per-paper time**

**Vị trí:**

- [Performance, cell 4, dòng 202](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/04_performance.ipynb:202): bảng benchmark không có dòng tổng thời gian discovery.
- Cell 4, dòng 206: gọi mean từng paper là **“end-to-end”**.
- Cell 5, dòng 229: nói thời gian đó bao gồm OAI metadata resolution.

**Bằng chứng:** [pipeline, dòng 438](C:/Users/ADMIN/Desktop/Do_an/arXivProject/src/crawling/pipeline.py:438) thực hiện discovery; đến dòng 456 mới bắt đầu `paper_started`. Vì vậy, **discovery ban đầu của các assigned papers nằm ngoài đồng hồ từng paper**. Việc lookup ngày reference sau đó có thể vẫn nằm trong đồng hồ này; phải phân biệt hai loại công việc.

JSON đã có `total_discovery_elapsed_seconds` tại [dòng 18](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/benchmark.json:18), nhưng chưa hiện trong báo cáo. Không nên đưa ngay số này lên trước khi sửa aggregation checkpoint.

**Cách sửa cụ thể:**

- Thêm dòng **Total entry discovery time** vào bảng benchmark.
- Đổi nhãn mean hiện tại thành thời gian xử lý source/references sau discovery, nếu giữ cách đo hiện có.
- Thêm đoạn mô tả ranh giới đo ngay trước bảng: discovery, per-paper processing, checkpoint và final export/backup.
- Giải thích vì sao tổng per-paper time khác batch wall time.

Đây là thiếu sót trực tiếp với [yêu cầu performance, dòng 353](C:/Users/ADMIN/Desktop/Do_an/arXivProject/ARXIV_PROJECT_FULL.md:353), vì đề nêu rõ **total time for entry discovery** và wall time toàn hệ thống.

---

**Các phần nên bổ sung, đặt chính xác ở đâu và vì sao đáng làm**

Không phải mọi đề xuất dưới đây là một mục bắt buộc riêng trong đề.

| Bổ sung | Đặt ở đâu | Nội dung tối thiểu và tác dụng |
|---|---|---|
| **Định nghĩa chỉ số và mẫu số** | Sau đoạn định nghĩa KPI ở Statistics cell 3, trước bảng cell 4 | Ghi công thức, cấp paper/version/reference, cách xử lý `no_tex`, lỗi và giá trị thiếu. Giúp người đọc hiểu chính xác mỗi tỷ lệ; đây là cách đáp ứng yêu cầu thống kê rõ ràng |
| **Ví dụ corpus thật** | Sau Methodology mục 3, đoạn kết ở dòng 52 | Một paper nhiều version và một trường hợp `no_tex`; chỉ ra metadata/source/references nằm đâu. Chứng minh tổ chức dữ liệu có thể dùng tiếp cho M2 |
| **Audit metadata** | Sau “Crawled Corpus Sample Preview”, Statistics cell 14 | Đếm thiếu title/authors/dates, kiểm kiểu list, ID null, version thiếu. Preview vài dòng đẹp chưa chứng minh chất lượng cả corpus |
| **Phân tích vài lỗi thật** | Ngay sau bảng lỗi của Statistics cell 10, đoạn bắt đầu dòng 925 | Mỗi loại chọn ID, thông báo lỗi gốc, điều đã xác minh, tác động và hướng xử lý. Biến bảng đếm thành phân tích |
| **Nguồn và ranh giới benchmark** | Performance sau cell 3, trước bảng cell 4 | Commit code, config, trạng thái run, cache mode, phạm vi RAM/disk và các bước nằm ngoài đồng hồ. Đáp ứng tính kiểm chứng được mà đề yêu cầu |
| **Trích dẫn tại chỗ** | Methodology mục 1, mục 3 và bảng policy | Gắn nguồn ngay vào phát biểu về OAI, ngày v1, pagination, rate limit. Danh mục cuối sách chưa chỉ rõ nguồn nào hỗ trợ câu nào |
| **Kết luận về corpus còn lại** | Thêm Markdown cell sau cell 9 của Performance | Nêu phần dùng được, lỗi chưa xử lý và ảnh hưởng đến M2/M3. Đây là đề xuất tăng chất lượng phân tích, không phải chương bắt buộc |

Riêng bảng schema ở [Overview, dòng 38](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/01_overview.md:38): báo cáo đang ghi nhiều trường `Nullable = No`, trong khi đề chỉ đánh dấu non-null rõ cho các ID. Nhóm có thể đặt ràng buộc nội bộ chặt hơn, nhưng phải nói **đó là quy tắc nhóm**, không trình bày như toàn bộ đều do đề bắt buộc.

**Có thêm hai ví dụ cụ thể cần sửa trong phần phân tích:**

- [Performance cell 6, dòng 493](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/04_performance.ipynb:493) giải thích paper chậm nhất có “5+ versions”. [Record thật](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/papers_detail.csv:19279) của `2601.23264` có **3 versions**, mất khoảng 669,08 giây.
- Cùng cell, dòng 486 giải thích paper nhanh nhất “no citations”. [Record thật](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/data/papers_detail.csv:18390) của `2602.00964` có **24 total references**, còn `kept_references = 0`.

Nên sinh các thuộc tính này từ record được chọn. Chưa có log xác nhận nguyên nhân chậm thì viết “có thể liên quan” và giới hạn suy luận; không điền sẵn nguyên nhân theo percentile.

Ở [Statistics cell 10, dòng 935](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/milestone1/03_corpus_stats.ipynb:935), HTTP 404 còn được diễn giải là withdrawn/unhosted. **404 chỉ xác nhận endpoint trả 404**, chưa xác nhận lý do. Giữ thông báo quan sát và giả thuyết ở hai cột riêng sẽ chặt chẽ hơn.

**Những chỗ giọng “AI” rõ và cách viết lại**

| Vị trí | Câu/cụm hiện tại | Nên sửa |
|---|---|---|
| [Trang chủ, dòng 12](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/book/content/index.md:12) | “this project pioneers…” | “This project collects versioned LaTeX sources and reference metadata for the assigned papers.” |
| Cùng file, dòng 49 | “strict engineering contracts” | Nêu việc thật: nhóm dùng chung crawler, chia bốn dải ID và tổng hợp kết quả |
| [README, dòng 3](C:/Users/ADMIN/Desktop/Do_an/arXivProject/arXiv-report/README.md:3) | “official, publication-grade” | “This repository contains the Jupyter Book report for…” |
| Statistics cell 1, dòng 13 | “Auditable Build-Time Guarantee”, “No … hardcoded numbers” | Mô tả đơn giản file đầu vào và bước tạo bảng/hình; bỏ bảo đảm tuyệt đối |
| Performance cell 9, dòng 628 | “completely eliminating the risk…” | Giới hạn kết luận vào peak đã quan sát và hạn chế sampling |

**Điều thuyết phục mình nhất không phải thay từ cho bớt “AI”, mà là để mỗi câu quan trọng truy ngược được về dữ liệu hoặc code thật.** Hiện báo cáo có nhiều thành phần tốt để làm điều đó; những vị trí trên là nơi lời viết đang vượt khỏi bằng chứng. Sửa đúng các chỗ này sẽ nâng độ tin cậy rõ hơn việc thêm trang hay thêm biểu đồ.
