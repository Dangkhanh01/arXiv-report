# Review QC — Template báo cáo Milestone 1

Ngày review: 24/10/2026.

## Phạm vi và kết luận

Đánh giá này áp dụng cho **template báo cáo được thử bằng 100 bài đã crawl**, không phải bản nộp hoàn chỉnh của toàn bộ 20.000 bài. Không trừ điểm vì dữ liệu hiện tại mới có 100 bài. Mục tiêu QC là kiểm tra template có đáp ứng report requirements của M1, tính và diễn giải chỉ số đúng, và có thể nhận dữ liệu đầy đủ về sau mà ít phải sửa tay hay không.

Nguồn yêu cầu: [Milestone 1 — Report Requirements (Jupyter Book)](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/#report-requirements-jupyter-book).

- Khi nộp M1, nội dung báo cáo cần tập trung vào M1. M2 bổ sung phần tiếp theo vào cùng Jupyter Book sau đó. M3 có yêu cầu poster riêng; không cần viết trước chương M2–3 để đạt yêu cầu report M1.
- Đã đọc các trang nội dung, notebook, dữ liệu mẫu, script đồng bộ và workflow deploy; build kiểm tra thành công, cả ba notebook thực thi được. Điều này xác nhận khả năng build, không thay thế kiểm tra trực quan giao diện hoặc xác nhận website đã được deploy công khai.
- Điểm đánh giá tham khảo: **6/10 cho độ sẵn sàng của template**, không phải điểm theo rubric chính thức và không phải điểm toàn bộ code crawler.
- Điểm tốt: khung Jupyter Book chạy được; hình và bảng thống kê được sinh từ dữ liệu; có timeline tài nguyên; công khai trạng thái sample.

> Nhận xét theo góc nhìn giảng viên khó tính: Đã dựng được một bộ khung chạy được. Nhưng phần diễn giải đang tự tin hơn bằng chứng, một số chỉ số chưa đúng yêu cầu, và lời hứa có đủ dữ liệu chỉ cần áp vào thì code chưa thực hiện được.

## 1. Chưa có bước gộp dữ liệu cả nhóm

**Vị trí:** `scripts/sync_data.py`, hàm `find_latest_report_zip()` (khoảng dòng 57–71), `sync_aggregated_tree()` (khoảng dòng 167–180), và mô tả đồng bộ trong `README.md`.

**Vấn đề:** Script tìm nhiều `report.zip` nhưng chỉ chọn một file lớn nhất, dùng thời gian sửa file làm tiêu chí phụ. Script không gộp nhiều lần chạy, nhiều thành viên, checkpoint hay retry. Nhánh “aggregated” chỉ copy các file đã được tổng hợp sẵn. Vì vậy, chưa thể coi script này là công cụ tự động tổng hợp toàn bộ dữ liệu nhóm.

**Câu hỏi người chấm sẽ đặt:** Ai tổng hợp 20.000 bài, bằng công cụ nào? Vì sao một ZIP lớn nhất có thể đại diện cho nhiều tài khoản và nhiều lần chạy?

**Cần sửa:**

- Có bước aggregation thực sự, hoặc mô tả rõ template chỉ nhận đầu vào đã tổng hợp và chỉ ra công cụ tạo đầu vào đó.
- Hợp nhất theo paper/version và có quy tắc chọn trạng thái mới nhất hoặc hợp lệ khi trùng dữ liệu giữa các run/retry.
- Tính lại tỷ lệ từ tử số và mẫu số; không lấy trung bình đơn giản tỷ lệ của các run có kích thước khác nhau.
- Giữ benchmark theo run/member và định nghĩa cách báo cáo chung. Không cộng tùy tiện RAM đỉnh hoặc wall time của các phiên chạy song song.

**Hoàn tất khi:** Nhận được nhiều run của nhiều thành viên, đầu ra không trùng paper/version, tổng số và các tỷ lệ có thể đối chiếu; báo cáo không âm thầm chọn một run làm đại diện cả nhóm.

## 2. Kết luận hiệu năng có số sai và khẳng định chưa có bằng chứng

**Vị trí:** `book/content/milestone1/04_performance.ipynb`, mục “Analysis & Discussion”.

**Vấn đề:**

- “network latency accounts for over 85%” chưa có dữ liệu phân rã thời gian để chứng minh. Cũng cần phân biệt network latency, thời gian chờ pacing và backoff.
- “~142 KB per version” không khớp `book/data/summary.json`: `average_source_bytes_after = 469022.33082706766`, tương đương khoảng **458 KiB/version**.
- Kết luận “guaranteeing” batch 5.000 bài an toàn từ một batch thử 100 bài là quá mạnh; chưa có phân bố kích thước, ngoại lệ và mô hình dung lượng đỉnh.

**Cần sửa:**

- Sinh số liệu diễn giải từ dữ liệu, tránh viết cứng con số thực nghiệm.
- Chỉ công bố phần trăm thời gian khi có phép đo tương ứng.
- Chuyển các nhận định chưa kiểm chứng thành giả thuyết hoặc ước lượng có điều kiện; nêu phạm vi và giới hạn suy rộng.
- Dùng đơn vị đúng: chia 1024 là KiB, chia 1024² là MiB.

**Hoàn tất khi:** Mỗi khẳng định định lượng truy ngược được đến phép tính hoặc log; phần chữ không mâu thuẫn bảng và hình.

## 3. Thiếu tổng thời gian entry discovery

**Vị trí:** `book/content/milestone1/04_performance.ipynb`, bảng benchmark; bộ dữ liệu đầu vào trong `book/data/`.

**Vấn đề:** Có wall time, thời gian xử lý trung bình, RAM và disk nhưng không hiển thị **tổng thời gian entry discovery**, một chỉ số được đề M1 yêu cầu rõ.

**Cần sửa:**

- Mang discovery time từ log/manifest của crawler sang dữ liệu report.
- Thêm dòng hiển thị tổng discovery time, đơn vị và phạm vi đo.
- Nói rõ discovery đã nằm trong end-to-end wall time hay được đo riêng; không cộng hai lần.
- Khi chưa có phép đo, hiển thị thiếu dữ liệu thay vì tự điền 0.

**Hoàn tất khi:** Có thể đọc trực tiếp tổng discovery time của batch đang báo cáo và đối chiếu với dữ liệu nguồn.

## 4. Hai số thời gian khác phạm vi nhưng chưa được giải thích

**Vị trí:** `book/content/milestone1/04_performance.ipynb`; `book/data/summary.json`, trường `average_paper_processing_seconds`; `book/data/benchmark.json`, trường `wall_seconds`.

**Bằng chứng trên sample:**

- End-to-end wall time: **6.324,64 giây**.
- Trung bình thời gian xử lý từng paper: **59,09 giây**.
- Wall time / 100 paper: **63,25 giây/paper**.
- Chênh lệch giữa wall time và tổng thời gian từng paper: khoảng **415,41 giây**.

**Vấn đề:** Hai cách đo có thể đều đúng khi khác phạm vi; không đủ cơ sở kết luận phép đo sai. Tuy nhiên, report chưa giải thích overhead và đang ghi “across all assigned papers” dù dữ liệu là batch mẫu.

**Cần sửa:**

- Phân biệt mean thời gian xử lý từng paper và end-to-end wall time trên mỗi paper.
- Ghi rõ mẫu số là số paper được đo trong batch.
- Giải thích discovery, khởi tạo, checkpoint, backup và các phần ngoài vòng xử lý paper được tính ở đâu; đối chiếu bằng log thay vì đoán nguyên nhân chênh lệch.

**Hoàn tất khi:** Người đọc hiểu hai số đo khác nhau vì đâu, mỗi số bao gồm công đoạn nào.

## 5. Đề hỏi kích thước trung bình theo paper, bảng chỉ trình bày theo version

**Vị trí:** `book/content/milestone1/03_corpus_stats.ipynb`, bảng KPI và mục “Storage Optimization”; `book/data/summary.json`.

**Vấn đề:** Report hiển thị “Avg Version Size”, trong khi yêu cầu M1 nêu average paper size trước/sau loại hình. Dữ liệu đã có thống kê theo paper nhưng chưa sử dụng:

- Trước lọc: khoảng **5.176.456 bytes/paper**.
- Sau lọc: khoảng **677.214 bytes/paper**.
- Mẫu số: **92 paper**.

Ngoài ra, nếu so sánh archive nén trước lọc với file giải nén sau lọc, chênh lệch không chỉ phản ánh dung lượng ảnh bị loại. Whitelist còn loại `.sty`, `.cls`, `.bbl` và các file khác.

**Cần sửa:**

- Hiển thị kích thước trung bình theo paper, ưu tiên có giá trị bytes để đối chiếu yêu cầu; giữ thống kê version làm bổ sung.
- Giải thích mẫu số 92 và cách xử lý paper có version lỗi hoặc `no_tex`.
- Ghi rõ trước/sau đo ở trạng thái nén hay giải nén và gồm loại file nào.
- Không diễn giải toàn bộ mức giảm dung lượng là dung lượng hình ảnh đã loại bỏ.

**Hoàn tất khi:** Đơn vị phân tích, mẫu số và cơ sở so sánh rõ ràng; chỉ số theo paper có mặt trong report.

## 6. Tên chỉ số và mẫu số dễ gây hiểu nhầm

**Vị trí:** `book/content/milestone1/03_corpus_stats.ipynb`, bảng KPI; cách tính trong `../src/crawling/metrics.py`, hàm `summarize_corpus()`.

**Vấn đề:**

- “Total Assigned Papers” dùng `papers_discovered = 100`, trong khi tổng được giao là 20.000; 100 thuộc batch mẫu.
- “Reference Jobs Success Rate = 100%” không chứng minh đã lấy đủ mọi tài liệu tham khảo thực tế trong bibliography.
- “Average Reference Completeness = 100%” có mẫu số **81**, nhưng bảng không hiện mẫu số này. Cách tính hiện tại phản ánh độ đầy đủ metadata của arXiv matching pool trên các paper đủ điều kiện, không phải mức bao phủ toàn bộ bibliography.
- “Paper success” theo cách tính hiện tại yêu cầu TeX thành công ở mọi version, khác với coverage chấp nhận `no_tex` hợp lệ; cần nói rõ để tránh hiểu sai 92%.

**Cần sửa:**

- Tách assigned, evaluated, discovered và completed.
- Với mỗi tỷ lệ, ghi định nghĩa, tử số, mẫu số và trường hợp bị loại.
- Đặt tên phân biệt thành công job API, lấy hết pagination, đầy đủ trường metadata và bao phủ bibliography.
- Hiển thị mẫu số của reference completeness và giải thích paper không có matching-pool reference được xử lý thế nào.

**Hoàn tất khi:** Không có tỷ lệ “100%” thiếu phạm vi; người đọc có thể tái tính từ dữ liệu nguồn.

## 7. Có version thất bại nhưng chưa phân tích

**Vị trí:** `book/data/summary.json`; `book/content/milestone1/03_corpus_stats.ipynb`.

**Bằng chứng:** 135 version dự kiến, 127 thành công có source, 6 `no_tex`, 2 thất bại; coverage hợp lệ là **98,52%**.

**Vấn đề:** Report nổi bật tỷ lệ coverage nhưng chưa trình bày đầy đủ breakdown và nguyên nhân hai version thất bại.

**Cần sửa:**

- Thêm bảng/biểu đồ trạng thái version: success, `no_tex`, failed, pending.
- Thêm bảng lỗi gồm paper ID, version, loại lỗi, trạng thái retry và hướng xử lý.
- Phân biệt `no_tex` được xác nhận hợp lệ với lỗi download hoặc định dạng chưa xử lý được.
- Khi dữ liệu thay đổi, bảng lỗi phải cập nhật từ nguồn thay vì viết tay.

**Hoàn tất khi:** Người chấm biết chính xác phần chưa đạt là gì, có sửa được không và tác động đến corpus như thế nào.

## 8. Có biểu đồ nhưng phân tích dữ liệu còn mỏng

**Vị trí:** `book/content/milestone1/03_corpus_stats.ipynb`; phần phân tích trong `04_performance.ipynb`.

**Vấn đề:** KPI, biểu đồ hai cột kích thước, donut references và preview 15 bài minh họa được pipeline, nhưng chưa cho thấy phân bố và ngoại lệ. Chỉ số trung bình che mất các paper/version rất lớn, rất chậm hoặc không có reference.

**Nên bổ sung:**

- Phân bố số version/paper.
- Phân bố kích thước source và các paper/version lớn bất thường.
- Phân bố số references/paper, gồm các paper có 0 references.
- Phân bố thời gian xử lý, các trường hợp chậm và lý do có bằng chứng.
- Nhận xét gắn với câu hỏi cụ thể và giới hạn của sample: 100 paper hiện đều thuộc Danh, từ `2606.15734` đến `2606.15833`, chưa đại diện mọi dải của nhóm.

Đây là đề xuất tăng chất lượng phân tích; không khẳng định từng biểu đồ trên đều là mục bắt buộc riêng của đề.

**Hoàn tất khi:** Report giải thích được đặc điểm và khó khăn của corpus, thay vì chỉ trưng bày vài số tổng hợp.

## 9. Đổi dữ liệu chưa tự cập nhật phần chữ

**Vị trí:** `book/content/index.md`, hai notebook M1 và các đoạn mô tả môi trường/kết luận.

**Vấn đề:** “100 papers”, phiên bản Python, mốc 400 MB và nhiều kết luận đang được viết cứng. Thay JSON/CSV sẽ cập nhật bảng/hình nhưng phần chữ có thể tiếp tục mô tả batch cũ.

**Cần sửa:**

- Có metadata chung cho chế độ sample/full, số paper, phạm vi ID, run ID, môi trường và cấu hình benchmark.
- Sinh các con số trong nội dung diễn giải từ dữ liệu khi phù hợp.
- Giữ bước rà lại nhận xét khi chuyển từ sample sang full corpus; nhận xét định tính không tự đúng chỉ vì biểu đồ đã cập nhật.
- Tránh tuyên bố “all figures and tables” theo nghĩa tuyệt đối khi một số bảng mô tả/team/schema vẫn là Markdown tĩnh; chỉ rõ yêu cầu sinh động được áp dụng cho hình/bảng kết quả thống kê.

**Hoàn tất khi:** Đổi bộ dữ liệu không để lại con số hoặc nhãn sample cũ gây mâu thuẫn trong báo cáo.

## 10. Nhập thiếu dữ liệu vẫn có thể báo thành công

**Vị trí:** `scripts/sync_data.py`, `verify_receipt()`, `sync_from_zip()`, `sync_aggregated_tree()` và thông báo thành công cuối script; tuyên bố hash-verified trong `README.md`.

**Vấn đề:**

- ZIP có file nào thì copy file đó; thiếu file không bị chặn. File cũ trong `book/data/` có thể còn lại và bị trộn với run mới.
- Không có receipt thì bỏ kiểm tra hash nhưng vẫn tiếp tục.
- Có receipt nhưng thiếu expected hash cũng chưa bảo đảm đã đối chiếu hash, dù script có thể in thông báo “Verified SHA-256 integrity”.
- Nhánh aggregated copy file không thực hiện đối chiếu receipt/hash như lời mô tả chung trong README.
- Notebook dùng nhiều giá trị mặc định 0; thiếu trường có thể bị thể hiện như kết quả thực nghiệm bằng 0 thay vì thiếu phép đo.

**Cần sửa:**

- Kiểm tra đủ bộ file, schema, trường bắt buộc, kiểu dữ liệu và tính nhất quán trước khi thay dữ liệu report.
- Mang run ID/provenance vào bộ dữ liệu để phát hiện trộn run.
- Cập nhật trọn bộ sau khi kiểm tra, tránh để bộ dữ liệu dở dang hoặc lẫn file cũ.
- Phân biệt rõ verified, unverified và failed; chỉ tuyên bố hash-verified khi có giá trị kỳ vọng để đối chiếu và đã khớp.
- Hiển thị thiếu dữ liệu hoặc dừng với lỗi có nghĩa khi thiếu phép đo bắt buộc.

**Hoàn tất khi:** Đầu vào thiếu/sai không thể sinh báo cáo trông hoàn chỉnh nhưng dùng lẫn dữ liệu cũ hoặc số 0 giả.

## 11. Mô tả phương pháp chưa đủ để đối chiếu triển khai

**Vị trí:** `book/content/milestone1/02_methodology.md`, đặc biệt phần reliability và tuyên bố “guarantee zero data loss”.

**Vấn đề:** Đã mô tả được OAI, selective extraction và S2 nhưng thiếu liên kết đến module/hàm triển khai, cấu hình batch, retry policy, resume và bằng chứng kiểm tra byte-exact/version coverage. Checkpoint định kỳ không tự chứng minh không mất bất kỳ dữ liệu nào khi Colab ngắt bất ngờ.

**Cần sửa:**

- Gắn từng cơ chế với module/hàm hoặc liên kết code ở revision cụ thể.
- Công khai cấu hình thực tế: pacing, retry/backoff, timeout, cache mode/TTL, checkpoint và resume.
- Nêu bằng chứng kiểm tra nội dung `.tex`/`.bib` giữ nguyên byte và kiểm tra toàn bộ version, gồm `no_tex`.
- Viết giới hạn bảo đảm backup đúng với cơ chế thực tế; phân biệt dữ liệu đã backup thành công và phần công việc sau checkpoint gần nhất.
- Gắn nguồn tham khảo với các khẳng định kỹ thuật cụ thể. Danh mục tài liệu cuối sách không thay thế hoàn toàn trích dẫn tại nơi sử dụng.

**Hoàn tất khi:** Người đọc có thể đối chiếu mô tả với code, cấu hình và bằng chứng thực nghiệm; không có bảo đảm tuyệt đối chưa chứng minh.

## 12. Chương M2–3 làm loãng bản M1 và có lỗi ở nội dung tương lai

**Vị trí:** `book/_toc.yml`, `book/content/index.md`, các trang `book/content/milestone2/` và `book/content/milestone3/`; riêng công thức ở `milestone3/01_overview.md`, khoảng dòng 45.

**Vấn đề:** Navigation hiện đưa nhiều trang kế hoạch M2–3 vào bản M1 dù chưa có kết quả. Có thêm các chương này không tự động là vi phạm yêu cầu, nhưng làm người chấm khó tập trung vào phần được nộp.

Trang M3 ghi rank bằng 0 khi không tìm thấy reference đúng rồi sử dụng `1/rank`. Điều này dẫn đến `1/0`; đúng phải là **đóng góp điểm bằng 0** nếu đáp án đúng không nằm trong top 5.

**Cần sửa:**

- Bản M1 nên tập trung navigation vào M1 và references; giữ roadmap tương lai ngắn nếu cần.
- Có thể giữ nguồn trang M2–3 để phát triển sau, nhưng điều chỉnh cấu hình xuất bản phù hợp để không đưa trang chưa hoàn thiện vào bản nộp.
- Sửa diễn giải MRR@5 theo từng trường hợp: reciprocal rank khi đáp án đúng nằm trong top 5; bằng 0 khi không nằm trong top 5.
- Phân biệt kế hoạch với kết quả đã thực hiện, tránh thì hiện tại tạo cảm giác pipeline tương lai đã chạy.

**Hoàn tất khi:** Người chấm mở book là nhận ra phạm vi M1 và tìm đủ nội dung M1; roadmap không chứa công thức sai hoặc bị hiểu thành kết quả thực nghiệm.

## Đối chiếu đầy đủ với ARXIV_PROJECT_FULL.md

Phần bổ sung này đối chiếu trực tiếp bản đề local `../ARXIV_PROJECT_FULL.md`, gồm Logistics/Regulations, Description của M1, Requirement, Submission Format, Report Requirements và cả năm Grading Criteria. Đây là checklist yêu cầu để sử dụng cùng 12 mục phân tích ở trên; **12 mục lỗi không tự thay thế checklist yêu cầu**.

Các vị trí nguồn chính trong bản đề tại thời điểm review:

- Logistics/Regulations: khoảng dòng 51–72.
- M1 Description: khoảng dòng 88–295.
- M1 Requirement và schema: khoảng dòng 297–315.
- Submission Format/Source Code: khoảng dòng 317–331.
- Report Requirements: khoảng dòng 333–339.
- Grading Criteria: khoảng dòng 341–353.

Trạng thái “có” dưới đây chỉ xác nhận nội dung/khả năng quan sát được trong template, không tự chứng nhận dữ liệu crawl đã đúng hoặc toàn bộ bài được giao đã hoàn tất. “Chưa xác minh” không có nghĩa là đã vi phạm.

### A. Yêu cầu báo cáo và README

| ID  | Yêu cầu trong đề                                                            | Trạng thái template hiện tại                                                                                       | Việc còn cần làm / mục QC                                                                                                                                               |
| :-- | :-------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R01 | Report là Jupyter Book                                                      | Có `_config.yml`, `_toc.yml`, Markdown và notebooks; build kiểm tra thành công                                     | Giữ kiểm tra build khi đổi dữ liệu/cấu hình                                                                                                                             |
| R02 | Repo report public riêng, tách repo code chung                              | Có repo Git local riêng trong `arXiv-report` và URL repo trong config; trạng thái public trên GitHub chưa xác minh | Xác minh repo thực tế public và tách repo code; không suy từ URL config rằng đã đạt                                                                                     |
| R03 | Host trên GitHub Pages của repo report                                      | Có workflow build/deploy và hướng dẫn; website public đang chạy chưa xác minh                                      | Kiểm tra lần deploy thực tế và URL Pages truy cập được                                                                                                                  |
| R04 | M1 là phần đầu book; M2 thêm phần tiếp theo về sau                          | Có phần M1; đang đưa cả kế hoạch M2–3 vào navigation                                                               | Không thiếu yêu cầu do chưa có kết quả M2–3; thu gọn navigation là đề xuất biên tập, mục 12                                                                             |
| R05 | Có thống kê **và phân tích** dữ liệu crawl                                  | Có KPI và biểu đồ; phân tích còn mỏng, có nhận định thiếu bằng chứng                                               | Sửa mục 2, 7, 8; đề không ấn định số lượng hay loại histogram cụ thể                                                                                                    |
| R06 | Hình/bảng kết quả sinh lúc compile, không dán screenshot                    | Các notebook được thực thi khi build và sinh bảng/Plotly; không dùng screenshot cho kết quả đang xét               | Tiếp tục kiểm tra output HTML và tương tác sau khi cập nhật; bảng team/schema tĩnh không phải bằng chứng thống kê thực nghiệm                                           |
| R07 | Mô tả quá trình triển khai, cách scraper hoạt động                          | Có discovery, download, extraction, references, checkpoint                                                         | Cần bổ sung mapping code/config, giới hạn và provenance; mục 11                                                                                                         |
| R08 | Mô tả công cụ, thư viện sử dụng                                             | Có OAI, S2, `tarfile`, `psutil`, công cụ hiển thị; mô tả thư viện triển khai chưa tập trung đầy đủ                 | Thêm bảng công cụ/thư viện thực sự dùng và vai trò; API, OAI và `requests` trong đề là ví dụ, không bắt buộc dùng tất cả                                                |
| R09 | Số paper crawl thành công                                                   | Có `full_source_papers = 92`                                                                                       | Định nghĩa rõ thành công theo paper và cách tính `no_tex`; mục 6, 7                                                                                                     |
| R10 | Overall success rate                                                        | Có `paper_success_rate = 92%`, version coverage là chỉ số khác                                                     | Hiển thị tỷ lệ quan sát đúng cột, tử số/mẫu số và phạm vi sample; mục 6                                                                                                 |
| R11 | Kích thước trung bình paper bằng bytes trước/sau loại hình                  | Dữ liệu có, report đang hiển thị chủ yếu theo version và KB                                                        | Bổ sung cặp chỉ số theo paper, bytes, mẫu số và cơ sở đo nén/giải nén; mục 5                                                                                            |
| R12 | Số references trung bình mỗi paper                                          | Có `32.22`, mẫu số 100                                                                                             | Nêu cách tính khi API lỗi, partial hoặc 0 references; mục 6                                                                                                             |
| R13 | Tỷ lệ thành công trung bình crawl reference metadata                        | Có job success `100%`; đồng thời có metadata completeness với mẫu số khác                                          | Định nghĩa rõ hai chỉ số; không coi chúng là độ bao phủ bibliography; mục 6                                                                                             |
| R14 | Tổng thời gian xử lý một paper                                              | Có mean và batch wall time; chưa trình bày thời gian của từng paper/một paper cụ thể trong report                  | Thêm bảng per-paper end-to-end elapsed time hoặc ví dụ paper có ID, scope rõ; dùng bảng per-paper còn hỗ trợ kiểm chứng mean; bổ sung mục 4                             |
| R15 | Thời gian trung bình xử lý các paper được yêu cầu                           | Có `59.09 s`, nhưng nhãn “all assigned” chưa đúng phạm vi sample và khác `wall/N`                                  | Giải thích phạm vi và mẫu số; mục 4                                                                                                                                     |
| R16 | Tổng thời gian entry discovery                                              | Chưa có trong report và bộ input report hiện dùng                                                                  | Bổ sung phép đo, field và bảng; mục 3                                                                                                                                   |
| R17 | RAM tối đa trong scraping                                                   | Có peak RSS và timeline; khớp peak của CSV sample                                                                  | Ghi là peak quan sát qua sampling, phạm vi process tree; không bảo đảm bắt được mọi peak ngắn                                                                           |
| R18 | RAM trung bình                                                              | Có mean khớp trung bình các mẫu CSV                                                                                | Nêu là sample mean; khoảng lấy mẫu thực tế không cố định chính xác 0,25 s, xem bổ sung bên dưới                                                                         |
| R19 | Dung lượng disk tối đa cần dùng                                             | Có observed peak disk và timeline                                                                                  | Nêu các đường dẫn/loại dữ liệu được tính, gồm staging/cache/index/backup nếu thuộc hệ thống; chưa suy từ một số tổng rằng mọi thành phần đã được bao phủ                |
| R20 | Dung lượng output cuối                                                      | Có `final_disk_bytes`                                                                                              | Định nghĩa output gồm corpus hay cả report/cache/archive; giải thích nếu khác điểm cuối timeline                                                                        |
| R21 | Phép đo runtime/RAM/disk kiểm chứng được                                    | Có JSON và CSV resource samples; thiếu per-paper/discovery/provenance trong repo report                            | Hoàn thiện mục 3, 4, 10, 11; giữ log/config hoặc dữ liệu đo tối thiểu đủ đối chiếu, không bắt buộc công bố toàn bộ corpus                                               |
| R22 | Nhiều chương trình: wall time end-to-end và memory toàn hệ thống            | Report có mô tả process tree; code sampler hỗ trợ parent + children                                                | Liệt kê thành phần trong/ngoài benchmark, worker backup, cache/index, discovery; process nằm ngoài cây tiến trình không tự được tính; cần xác minh cấu hình run thực tế |
| R23 | Benchmark cuối trên Google Colab CPU-only                                   | JSON ghi Colab và `cpu_only: true`; sample chưa phải benchmark cuối                                                | Hiển thị giá trị thực từ metadata, kèm cấu hình/bằng chứng runtime; không coi một chuỗi environment là xác minh độc lập                                                 |
| R24 | Disk không vượt giới hạn instance Colab; không có trần runtime do đề áp đặt | Có số disk sample; chưa có capacity/free-space của runtime để đối chiếu                                            | Ghi giới hạn/dung lượng khả dụng thực tế và so sánh observed peak; bỏ bảo đảm 5.000 bài chưa chứng minh, mục 2                                                          |
| R25 | README riêng: Python, package setup, cách chạy với cấu hình cụ thể          | README report có hướng dẫn build/sync; README repo code có cấu hình crawler/Colab                                  | Liên kết rõ hai repo/README; người đọc phải tìm được lệnh/notebook chạy crawler và cấu hình batch. Không bắt README report chứa lại toàn bộ code crawler                |

### B. Yêu cầu crawler/corpus cần có bằng chứng khi chấm M1

Các mục dưới đây là yêu cầu thực hiện của M1, không phải yêu cầu phải có một chương độc lập cho mỗi dòng. Template có thể trình bày bằng bảng audit, ví dụ và liên kết code. Chưa thể kết luận chúng đã đạt chỉ vì report mô tả đúng ý tưởng.

| ID  | Yêu cầu trong đề                                                                               | Report hiện tại và điểm cần kiểm chứng                                                                                                                                                                                     |
| :-- | :--------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Resolve đúng dải ID được giao; không bắt harvest toàn arXiv                                    | Có bảng dải ID; cần đối chiếu manifest với assignment, không chỉ đếm paper                                                                                                                                                 |
| D02 | Crawl mọi version, kể cả v1                                                                    | Có tổng version và mô tả endpoint versioned; cần danh sách expected/observed theo paper/version và xử lý hai version lỗi trong sample                                                                                      |
| D03 | Thu full-text source, metadata, BibTeX/source `.bib`, reference information                    | Có mô tả `.tex`/`.bib` và S2; bổ sung inventory/audit file và mapping metadata theo version. Không nhầm giữ `.bib` ở M1 với chuyển `\\bibitem` sang BibTeX ở M2                                                            |
| D04 | Chỉ extract `.tex`/`.bib`; giữ nguyên figure commands trong TeX                                | Mô tả đúng; cần bằng chứng whitelist và byte-exact thay vì chỉ khẳng định                                                                                                                                                  |
| D05 | Version không có TeX phải giữ record rỗng, không bỏ publication                                | Có mô tả `no_tex`; cần ví dụ/audit phân biệt nguồn không có TeX với download lỗi                                                                                                                                           |
| D06 | Crawl reference metadata qua Semantic Scholar cho mỗi publication                              | Có endpoint, pagination, thống kê job; cần mapping kết quả về publication/version trong tổ chức local và nêu giới hạn S2 không phân biệt version                                                                           |
| D07 | Giữ mọi crawled reference local; chỉ arXiv-keyed reference vào bảng `references` cuối          | Có dual-store và donut; kiểm tra số hàng/schema thực tế và mapping `paperId` sang `ref_s2_id`                                                                                                                              |
| D08 | Giữ đủ title, authors, submission/revision dates, venue khi có và metadata reference tương ứng | Có bảng đặc tả; chưa có audit đầy đủ field/type/missingness trong template                                                                                                                                                 |
| D09 | Chuẩn bị đủ cột `papers` và `references` theo schema M1 cho xuất cuối M3                       | Tên cột trong overview phù hợp; overview tự ghi non-null cho nhiều trường hơn đề nêu rõ. Phải phân biệt ràng buộc nội bộ nhóm với ràng buộc đề, không tự loại reference hợp lệ vì thiếu field mà đề chưa đánh dấu non-null |
| D10 | Tổ chức corpus đủ thông tin per-publication/per-version                                        | Report chưa có ví dụ cây thư mục thực tế và mapping file → paper/version. Cấu trúc folder trong đề là gợi ý, nhóm được tự chọn; không bắt buộc đúng tên `2310-12345`                                                       |
| D11 | Giữ identifier cũ trước 2007 khi gặp                                                           | Phần Description M1 đề cập; thêm quy tắc và ví dụ nếu reference pool có ID dạng `hep-th/9901001`, không ép tất cả thành ID số mới                                                                                          |
| D12 | Download qua export mirror, request pacing, descriptive User-Agent, xử lý rate limit           | Có mirror và pacing; report chưa ghi đầy đủ User-Agent, pacing/retry riêng S2. Bổ sung cấu hình thực dùng và xử lý 429/Retry-After; không cần benchmark tốc độ bằng cách tăng request vượt chính sách                      |

### C. Điều kiện nộp bài và năm tiêu chí chấm

| ID  | Điều kiện/tiêu chí                                                                           | Kết luận QC                                                                                                                                                                        |
| :-- | :------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S01 | Một repo code public chung, commit tích lũy qua các milestone                                | Cần xác minh repo remote/public và lịch sử thực tế; không được kết luận từ report local                                                                                            |
| S02 | Repo code chứa source và hướng dẫn/dependencies, loại data/compiled/non-source theo quy định | Cần audit **file được track/push**, không chỉ file có trên máy. Không đánh đồng JSON/CSV số liệu phục vụ build trong repo report với toàn bộ corpus bị cấm nộp trong repo code     |
| S03 | Nộp Moodle theo nhóm: link repo code và link report public, đúng hạn                         | Là điều kiện nộp; chưa kiểm tra thao tác Moodle. Ghi checklist trước nộp, không tự cho là đã hoàn thành                                                                            |
| S04 | Ngôn ngữ theo chương trình; trích dẫn đầy đủ, tự hiểu và tự diễn giải                        | Report hiện tiếng Anh và có danh mục nguồn. Cần bảo đảm phù hợp ngôn ngữ chương trình và nguồn gắn với nội dung sử dụng; không kết luận có gian lận chỉ vì văn phong hoặc template |
| S05 | Không nộp data trung gian ở M1                                                               | Không yêu cầu upload Hugging Face ở M1; không trừ điểm vì chưa có final dataset/poster                                                                                             |
| G01 | Report (Jupyter Book)                                                                        | Đối chiếu R01–R25; build được chưa có nghĩa đủ chỉ số hoặc diễn giải đúng                                                                                                          |
| G02 | Source Code: sạch, dễ đọc, chạy được                                                         | Review này mới kiểm tra phần report/sync và khả năng build, không chứng nhận toàn bộ crawler. Cần đánh giá code crawler riêng nếu muốn chấm đủ M1                                  |
| G03 | Discovery & Crawling: phương pháp phù hợp, full version coverage                             | Đối chiếu D01–D06, D11–D12 và audit thực tế; sample chỉ chứng minh trong phạm vi được kiểm tra                                                                                     |
| G04 | Resulted Data: mức độ thành công và tổ chức corpus                                           | Đối chiếu D03–D10; cần audit corpus/schema, không chỉ sơ đồ và bảng đặc tả                                                                                                         |
| G05 | Scraper's Performance: hiệu quả so với nhóm khác                                             | Cần số đo Colab CPU có thể so sánh và giới hạn rõ; chưa có kết quả nhóm khác thì chưa thể kết luận hơn/kém. Không tự thêm yêu cầu phải có baseline đối thủ nếu không có dữ liệu    |

### D. Những điểm cần bổ sung sau lần đọc lại

1. **Per-paper runtime:** Bổ sung dữ liệu và bảng thời gian từng paper/một paper có ID, không coi batch wall time hoặc mean là đủ thay cho mọi ý của yêu cầu thời gian.
2. **Phạm vi đo toàn hệ thống:** Ghi rõ discovery, worker checkpoint/upload, temporary extraction, index/cache, final export và backup có nằm trong benchmark hay không. README code cho biết final notebook export/backup nằm ngoài crawl benchmark; report cần mô tả nhất quán và giải thích ranh giới, không gọi toàn bộ mọi hoạt động là đã bao gồm nếu chưa đo.
3. **Sampling RAM:** CSV sample có median khoảng cách mẫu khoảng **0,309 s**, gap lớn nhất khoảng **7,651 s**; `0.25` là interval cấu hình, không phải cam kết chu kỳ thực tế chính xác. Mean hiện là trung bình mẫu; nên ghi rõ hoặc tính mean có trọng số thời gian nếu muốn diễn giải mức tiêu thụ trung bình theo thời gian. Peak lấy mẫu có thể bỏ lỡ spike ngắn. Đây là làm rõ phương pháp kiểm chứng, không có nghĩa đề bắt buộc thuật toán tích phân cụ thể.
4. **Disk cuối và timeline:** Mẫu timeline cuối ghi **77.174.446 bytes**, `final_disk_bytes` ghi **79.196.837 bytes**. Có thể là hai thời điểm/phạm vi đo khác nhau; cần giải thích từ log, không mặc định đó là lỗi tính toán. Nêu capacity/free-space của instance để đối chiếu giới hạn Colab.
5. **Bằng chứng CPU-only:** Table đang in environment nhưng không trực tiếp hiển thị `cpu_only`/cache mode từ JSON. Thêm các field này và cấu hình run; không gán giá trị mặc định “Colab CPU-only” khi thiếu bằng chứng.
6. **Schema/missingness và layout:** Thêm audit hoặc ví dụ dữ liệu thật cho metadata, mapping source/BibTeX/reference theo paper/version, ID cũ và xử lý null; đề không bắt xuất final Parquet/Hugging Face ngay M1.
7. **Public hosting và reproducibility:** Xác minh repo/public Pages, link code, README crawler và cấu hình chạy thực tế trước khi đánh dấu yêu cầu đã đạt.

### E. Phân biệt yêu cầu bắt buộc và đề xuất QC

- **Yêu cầu trực tiếp:** Jupyter Book public riêng trên Pages; thống kê/phân tích; hình/bảng kết quả sinh khi compile; mô tả triển khai/công cụ; các số đếm/tỷ lệ/kích thước/time/RAM/disk nêu trong R09–R24; README setup/run; đúng phạm vi crawl/version/corpus và điều kiện nộp.
- **Đề xuất cách đáp ứng hoặc tăng chất lượng:** Các histogram cụ thể, bảng lỗi chi tiết, mapping tới hàm code, metadata/provenance tập trung, validation đầu vào, số liệu diễn giải sinh động. Đề có thể yêu cầu kết quả kiểm chứng được nhưng không ấn định duy nhất những hình thức triển khai này.
- **Theo mục tiêu riêng của template:** Tự gộp multi-run/multi-member và thay dữ liệu ít sửa tay. Đề không bắt aggregation phải nằm trong repo report; có thể dùng công cụ ngoài nếu mô tả và đầu ra đúng.
- **Biên tập tùy chọn:** Ẩn M2–3 khỏi bản M1 để tập trung. Có chương tương lai không tự động vi phạm đề.
- **Không phải yêu cầu M1:** Hoàn thành parser/dedup M2, feature engineering/model/MRR M3, upload final dataset, nộp poster; không bắt harvest toàn arXiv hay dùng mọi API/thư viện ví dụ trong đề.

**Kết luận sau đối chiếu:** Khung bốn phần M1 (overview, methodology, corpus stats, performance) có thể chứa đủ yêu cầu báo cáo mà không cần thêm chương M2–3. Tuy nhiên, nội dung hiện tại **chưa đủ để đánh dấu hoàn tất tất cả Report Requirements**, và 12 mục review ban đầu cần được dùng cùng ma trận này. Sau khi sửa, phải kiểm tra từng hàng bắt buộc và bằng chứng tương ứng; không chỉ đếm số mục lỗi đã đóng.

## Thứ tự xử lý đề nghị

1. Làm rõ/hoàn thiện aggregation và kiểm tra đầu vào: mục 1, 10.
2. Bổ sung đủ chỉ số bắt buộc và định nghĩa phạm vi đo: mục 3, 4, 5, 6.
3. Sửa số liệu sai, bỏ kết luận thiếu bằng chứng và phân tích lỗi: mục 2, 7, 11.
4. Làm nội dung cập nhật theo dữ liệu và bổ sung phân tích: mục 9, 8.
5. Thu gọn phạm vi xuất bản M1 và sửa nội dung tương lai: mục 12.
