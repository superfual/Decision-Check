# Kiến trúc đích Hybrid DeWeb + Verifiable Decision Engine

Phạm vi đối chiếu là mã nguồn tại `225e15c`. Tài liệu này mở rộng [roadmap](ROADMAP.md) cho hướng Hybrid. Hai phần có thể kiểm chứng độc lập: nội dung được phân phối qua DeWeb và phép đánh giá một quy tắc quyết định trên đầu vào đã mã hóa.

## Đối chiếu hiện trạng

| Lớp | Đã có | Cần bổ sung |
| --- | --- | --- |
| Giao diện | Các trang HTTPS tĩnh EN/VI/ZH, nhập danh mục, chuyển dữ liệu cùng tab có TTL 30 phút và nhập báo cáo. `site/market-agents.js` và `site/brain.js` tải Pyodide 0.27.7 từ CDN. | Manifest phát hành, gói thử nghiệm DeWeb và kiểm tra khả năng chạy trong TapeKit. |
| Dữ liệu và phân tích | Bộ thu thập Spot/USD-M công khai, hồ sơ nến đóng, Wyckoff và SMC dùng chung snapshot, Portfolio Insider dùng Decimal. Có các bản sao Python cho trình duyệt. | Kiểm tra đồng nhất Python/browser cho các đường chạy tương ứng. Ghi rõ cutoff, nguồn và dữ liệu tự khai trong gói kiểm chứng. |
| Tái lập | Báo cáo thị trường có checksum và trình phát lại Python, lưu SQLite cục bộ. `evaluate_three` tính lại ba nhánh, kiểm tra phạm vi/thời gian và ghi hash đầu vào. | Verifier độc lập cho báo cáo ba nhánh, ghim ruleset, revision và cách mã hóa. Kiểm tra hash theo một tham chiếu đáng tin. |
| Quy tắc | `boolean_gate` mô phỏng AND sáu bit từ 10 cổng NAND. Có các phép kiểm định lượng ứng viên. Futures thiếu xác minh margin/thanh lý giữ trạng thái UNKNOWN. | Đặc tả fixed-point, netlist có thể tái tạo, đối chiếu mẫu với tham chiếu phần mềm và bằng chứng đọc đúng mạch tại block đã ghim. |
| DeWeb/X Layer | Hướng triển khai được nêu trong roadmap. | Kiểm tra manifest, danh tính container, quyền cập nhật và phụ thuộc giao thức. Xác minh deployment bằng đọc chain trước khi ghi nhận hỗ trợ. |

## Thiết kế đề xuất

1. **Phân phối.** Giữ luồng HTTPS hiện tại. Tạo bản phát hành DeWeb chỉ đọc từ cùng revision, ban đầu gồm trang công khai, mô tả ruleset và ví dụ tổng hợp. Manifest liệt kê đường dẫn, kích thước, SHA-256 và revision. Ghi nhận chain ID, container, tham chiếu phiên bản và block theo giao thức. Thử riêng module/worker/WASM, nguồn ngoài, import file và lưu trữ cùng tab trong viewer. Mở rộng sang tính toán tương tác sau khi các khả năng đó được xác minh hoặc runtime có thể đóng gói tương thích. [TAP-10, bản nháp](https://github.com/TapeOutProtocol/TAPs/blob/main/TAPs/TAP-10.md) · [TapeKit previewer](https://tapeout.link/tapekit/)
2. **Tính toán ngoài chain.** Giữ OHLCV, phân tích heuristic và dữ liệu danh mục ở các đường chạy hiện có. Hai nhánh thị trường dùng cùng snapshot đã qua kiểm tra. Ghép kết quả tại `evaluate_three`, giữ ba trạng thái RULES_MET, RULES_NOT_MET và UNKNOWN. Mỗi kịch bản cho khoản đầu tư khác tạo đầu vào riêng.
3. **Gói kiểm chứng.** Đề xuất schema phiên bản mới đi kèm báo cáo. Gói cục bộ lưu tham chiếu snapshot, cutoff, ruleset, code revision, tham số, quy tắc chuẩn hóa và hash, sáu bit có thứ tự, trạng thái và kết quả. Khi có kiểm tra chain, bổ sung chain ID, danh tính mạch/triển khai, phiên bản encoding, block number/hash, input/output và phạm vi quy tắc. Định nghĩa byte chính xác trước khi triển khai, có test vector Python/JS. Dữ liệu danh mục, số dư và hash danh mục dễ đoán ở lại cục bộ. Nếu đầu vào công khai làm lộ giá trị riêng tư, dùng vector tổng hợp cho bản thử nghiệm.
4. **Kiểm chứng trên X Layer.** Bắt đầu với các vector tổng hợp cho AND sáu bit và một comparator cho lỗ dự kiến ≤ ngân sách. Chốt đơn vị, scale, bit width, dấu, endian, rounding và chính sách từ chối overflow trước khi thiết kế. Đọc mạch tại block đã ghim và đối chiếu danh tính, encoding, input/output với bản tham chiếu. Phép kiểm trên chain xác nhận quy tắc đã mã hóa đối với input đó. Nguồn nến và độ đầy đủ của danh mục có phạm vi xác thực riêng.
5. **Hiển thị.** Hiển thị riêng trạng thái phân tích, replay cục bộ, kết quả kiểm tra chain và nguồn đầu vào. Sai chain/mạch/block, lỗi RPC, thiếu dữ liệu hoặc sai phiên bản trả trạng thái kiểm chứng thất bại hoặc chưa thực hiện theo nguyên nhân. Kiểm tra tính toàn vẹn nội dung phát hành độc lập với việc mạch đã chạy.

## Thứ tự triển khai và tiêu chí nghiệm thu

| Bước | Bằng chứng cần có để review |
| --- | --- |
| 1. Gói kiểm chứng cục bộ | Replay cùng đầu vào cho cùng kết quả. Vector kiểm tra đúng ngưỡng, sai cutoff, sai phạm vi, sửa một byte, phiên bản lạ, trạng thái UNKNOWN và futures. So sánh các đường chạy CLI và browser. |
| 2. DeWeb chỉ đọc | Manifest tái tạo từ revision ghim. Đọc lại các byte tại block đã công bố và so hash. Mở EN/VI/ZH trong TapeKit, kiểm tra hành vi với CDN/storage bị chặn. |
| 3. TapeOut thử nghiệm | So đủ 64 tổ hợp sáu bit và các biên comparator với tham chiếu cục bộ. Đo gate count, calldata và chi phí. Ghi lại interface, đầu mối có quyền nâng cấp và phạm vi đã kiểm tra. |
| 4. Tích hợp verifier | Xác minh độc lập từ gói mẫu và dữ liệu đọc chain. Hiển thị phạm vi kiểm tra, trạng thái lỗi và cả đường replay khi RPC không khả dụng. |

Bước 2 và phần thiết kế của bước 3 có thể thực hiện song song. Phát hành container hoặc triển khai có phí cần một quyết định triển khai riêng sau khi review.
