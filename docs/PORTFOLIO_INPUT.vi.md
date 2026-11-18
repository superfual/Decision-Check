# Danh mục trước, kế hoạch sau

Trang manual.html thay luồng nhập một tài sản cũ bằng hai bước:
1. Mô tả danh mục hiện tại: nhiều coin/token, cả stablecoins, số lượng, giá vốn, hiện giá, PnL chưa thực hiện; PnL đã chốt nhập riêng.
2. Kế hoạch đầu tư tiếp theo: Spot hoặc Futures, tài sản bất kỳ, kể cả chưa sở hữu.

Ví dụ 10 OKB giá vốn 100, hiện giá 80 và 1.200 USDT cho NAV 2.000 USD, PnL chưa thực hiện −200 USD. Muốn mua BNB là BUY_SPOT với position_id=null, không thêm BNB giả vào lượng đang giữ.

Futures: số dư ví chưa cộng PnL + PnL chưa thực hiện = equity. Ký quỹ đã ở trong số dư ví; không cộng thêm lần nữa. Hiển thị số vị thế long/short, tổng ký quỹ và margin khả dụng. Không nhập trùng ví Futures thành tài sản USDT spot. Hiện một tài khoản Futures tuyến tính USDT, giả định tỷ giá 1 USD; options và inverse chưa hỗ trợ.

Tổng user nhập là số đối chiếu, không thay thế dữ liệu từng dòng. Sai lệch hơn 0,01 USD phải sửa trước khi phân tích. Các dòng cùng tài sản và nơi giữ cần gộp theo giá vốn bình quân; không nhập trùng. PnL đã thực hiện là ghi chú lịch sử, không cộng lại vào NAV. Snapshot chưa phải đối soát sổ giao dịch, phí, funding và nạp/rút.

Số lượng stablecoin khả dụng nhập riêng. Mỗi tài sản/vị thế đang giữ cần giá kịch bản chu kỳ; user xác nhận trước khi chạy. UI chuẩn hóa tới 12 chữ số thập phân; bộ não Python Decimal thực hiện kiểm tra rủi ro. Dữ liệu chỉ trong bộ nhớ trang, không tự lưu, không gửi tài khoản lên máy chủ.

## Cách hỏi ngưỡng chịu lỗ

UI hỏi mức lỗ tối đa chấp nhận trước khi cắt lỗ theo % giá vốn bình quân (Spot) hoặc entry (Futures), không gọi là “giá kịch bản chu kỳ”. Hệ thống tự đổi ra giá: long/spot = giá vốn × (1 − tỷ lệ); short = entry × (1 + tỷ lệ). Ví dụ OKB giá vốn 100, chịu lỗ 40% thì giá tương ứng 60. Phần trăm này không phải ROI ký quỹ hoặc tỷ lệ giảm NAV; ngân sách toàn danh mục vẫn được kiểm tra riêng. Nếu hiện giá đã vượt ngưỡng này, không được coi ngưỡng phía có lợi hơn hiện tại là rủi ro tương lai. UI đánh dấu đã chạm và không duyệt phương án mới.

Bỏ ô nhập PnL đã thực hiện. UI chỉ tính PnL chưa thực hiện từ số lượng, giá vốn bình quân/entry và hiện giá; hiển thị số tiền cùng tỷ lệ. Ngưỡng cắt lỗ chỉ là đầu vào phân tích, không đặt lệnh hoặc bảo đảm giá khớp.
