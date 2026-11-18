# Workflow Agentic Coding

1. **Định phạm vi.** Đọc [kiến trúc Hybrid](HYBRID_DEWEB.vi.md), chọn một bước và ghi tiêu chí nghiệm thu. Ghi commit gốc và kết quả kiểm thử trước khi sửa. Tạo nhánh từ `main` cho thay đổi đó.
2. **Chọn skill theo đầu ra.** Dùng `$decision-check-replay` cho report và verifier, `$decision-check-deweb` cho phát hành vào viewer, `$decision-check-tapeout` cho encoding, netlist và đọc chain. Khi giao việc, nêu đầu vào đã ghim, đường chạy cần kiểm tra và bằng chứng cần đính kèm PR.
3. **Làm một lát cắt có thể review.** Giữ tương thích report v1 và các đường nhập hiện có. Khi thay code dùng chung, kiểm tra cả bản CLI lẫn những bản Python được đóng gói dưới `site/`. Với hành vi mới ảnh hưởng giao diện, kiểm tra EN/VI/ZH và các trạng thái lỗi.
4. **Chạy kiểm thử và ghi kết quả.** Chạy lệnh bên dưới. Thay đổi web chạy thêm flow nhập tay → phân tích → chuyển trang → xuất hoặc nhập báo cáo tương ứng. Ghi fixture, lệnh, kết quả thực tế và trở ngại môi trường trong PR. Nếu có RPC hoặc viewer, ghi network, phiên bản viewer và read block.
5. **Mở PR vào `main`.** Nêu hành vi thêm mới, đường tương thích đã kiểm, bằng chứng và việc còn mở. Để người duy trì review và quyết định merge.

```sh
python -m unittest discover -s tests
node --test tests/manual-core.test.mjs tests/portfolio-input.test.mjs tests/workflow.test.mjs
python -m http.server 8080 --directory site
```

Trên môi trường hạn chế tạo tiến trình, Node 24 hỗ trợ `--test-isolation=none`. Khi bộ Python trên Windows gặp lỗi khi xóa SQLite, ghi lỗi và chạy lại trên hệ điều hành khác nếu có. Mọi thay đổi cách mở/đóng SQLite nên có PR và kiểm thử riêng.

Các skill của coding agent nằm trong `.agents/skills/`. Thư mục `agents/` mô tả logic của ba agent phân tích trong sản phẩm.
