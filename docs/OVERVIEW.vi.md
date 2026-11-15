# Decision Check — Hướng phát triển

Nhà đầu tư cần hiểu bằng chứng tín hiệu, theo dõi giá vốn và lãi/lỗ, đồng thời biết phương án mua thêm có phù hợp với danh mục không.

Sản phẩm đề xuất kết hợp:

1. Agent Wyckoff–SMC đã có: bằng chứng, điều kiện đạt/chưa đạt và trạng thái thiếu dữ liệu.
2. Bộ quản lý danh mục: giá vốn, PnL đã/chưa thực hiện, tiền dự phòng và ngân sách rủi ro.
3. TapeOut: kiểm tra những quy tắc cụ thể mã hóa thành mạch công khai.

Hiện đã có site EN/VI/中文 với dữ liệu nhập tay, giá vốn bình quân, PnL chưa thực hiện và kiểm tra tiền mặt/tỷ trọng. Chưa kết nối agent, tài khoản hay triển khai mạch mới cho Decision Check.

Tiếp theo: nhập báo cáo agent thật → hoàn thiện sổ giao dịch → thử mạch so sánh số → cung cấp bản ghi chạy lại.

Ví dụ: thị trường đạt điều kiện nhưng mua thêm khiến tỷ trọng lên 60%, vượt giới hạn 40%; kết quả là chưa đáp ứng quy tắc. Đây không phải bảo đảm về giá tương lai.

Chỉ cùng dữ liệu và phiên bản tính toán xác định mới có thể tái lập cùng phép kiểm tra. Circuit không tự chứng minh dữ liệu tài khoản đầy đủ hoặc nhận định thị trường đúng.

Xem [lộ trình](ROADMAP.md) và [kiến trúc](ARCHITECTURE.md).
