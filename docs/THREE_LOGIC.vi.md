# Decision Check: ba bộ não và đầu vào chuẩn bị cho TapeOut

## Phân công

- Wyckoff: bối cảnh, trading range và chuỗi sự kiện theo quy tắc đã chọn.
- SMC: cấu trúc, thanh khoản, sự kiện có thứ tự và vùng giá còn hợp lệ.
- Portfolio Insider: giá vốn/PnL, hai ngân sách rủi ro, toàn danh mục và phương án.

Hai agent thị trường không đọc kết quả của nhau và không tự lấy hai nguồn khác
nhau. `run_market_brains` đưa bản sao của cùng snapshot hợp lệ cho mỗi agent.
Một agent lỗi không ép agent còn lại ngừng phân tích. Phiên bản cũ vẫn giữ để
không thay đổi kết quả Replay v1.

## Dữ liệu đi trước phân tích

`profile_data.collect_profile` lấy một đồng hồ máy chủ, đúng symbol/product và
các timeframe được khai báo. Chỉ dùng nến đóng; kiểm tra OHLCV hữu hạn, thứ tự,
trùng lặp, khoảng trống, đủ số lượng và nến cuối không cũ. Tuần tính từ thứ Hai
UTC; tháng tính theo lịch thật, không giả định một tháng bằng 30 ngày. CYCLE cần
60 tháng lịch sử; coin mới thiếu lịch sử trả thiếu dữ liệu, không ép chạy.

Hiện adapter công khai chỉ Binance Spot và USD-M. Không đọc tài khoản cá nhân.
Không đổi Futures sang Spot khi bị chặn. Import do user cung cấp chỉ kiểm tra
được tính nhất quán; nhãn nguồn/hash không chứng minh dữ liệu là thật. Snapshot
không phải giá khớp lệnh tương lai. Chỉ kiểm tra tài sản user chọn, không quét toàn
thị trường. Dữ liệu danh mục vẫn theo phạm vi nhập tay đã chốt.

## TRUE là gì?

TRUE chỉ là đáp ứng toàn bộ điều kiện của phiên bản quy tắc này. False nghĩa
chưa đạt thiết lập, không nhất thiết nên bán. UNKNOWN nghĩa thiếu/không hợp lệ;
không được đổi UNKNOWN thành một tín hiệu thật. BULLISH/BEARISH mô tả thiên hướng,
không đồng nghĩa pass. Điểm confidence cũ không phải xác suất có hiệu chuẩn.

Quy tắc chi tiết tại `agents/wyckoff/README.md` và `agents/smc/README.md`.
Các mức swing/range là vùng vô hiệu hóa tham khảo, không phải dự báo giá tháng
sau. Chưa có mô hình xác suất, order book, funding, onchain whale hay options.

## Ghép với Portfolio Insider

`decision_logic.evaluate_three(portfolio_input, snapshot)` tự chạy lại cả ba
bộ tính từ đầu vào. Kiểm tra symbol, asset, venue, product, profile và độ lệch giữa
snapshot thị trường với thời điểm danh mục không quá một giờ. Đây là liên kết
phạm vi/thời gian, chưa chứng minh danh mục đầy đủ hoặc giá mua chắc chắn đúng.

Xuất sáu bit:

| Nhánh | Bit hợp lệ | Bit đạt |
| --- | --- | --- |
| Wyckoff | W_valid | W_pass theo hướng đang xét |
| SMC | S_valid | S_pass theo hướng đang xét |
| Danh mục | P_valid | P_pass cho khoản user yêu cầu |

Kết quả = W_valid AND W_pass AND S_valid AND S_pass AND P_valid AND P_pass.
Bộ mô phỏng NAND dùng 10 cổng hai đầu vào và kiểm thử đủ 64 tổ hợp. Đây là **mô
phỏng logic ứng viên**, chưa phải netlist đã biên dịch theo TAP, chưa có circuit ID,
chưa deploy hay gọi TapeOut. Việc bóc tách OHLCV và các phép tính danh mục hiện vẫn
ở Python; mạch dự kiến kiểm tra tổ hợp bit, không tự chứng minh phần bóc tách đúng.
Bước sâu hơn cần chuẩn hóa số nguyên/fixed-point, giới hạn bit, overflow, rounding
và circuit comparator thực tế cho lỗ ≤ ngân sách, NAV kịch bản ≥ sàn NAV.

Danh mục được xét theo khoản **yêu cầu**, không tự lấy khoản đã thu nhỏ để phê
chuẩn yêu cầu cũ. User muốn chọn khoản nhỏ hơn phải lập phương án mới. Futures
vẫn có phân tích nhưng kết quả ghép để UNKNOWN vì thanh lý và margin chưa xác
minh. Không hiển thị giả là đã chứng minh an toàn bằng circuit.

## Chạy và chạy lại

```sh
python3 -m decision_check.market_brain_cli --collect BNBUSDT --market SPOT --profile SWING --out /tmp/bnb.json
python3 -m decision_check.market_brain_cli --snapshot examples/market-brains/swing-synthetic.snapshot.json --out /tmp/replay.json
python3 -m decision_check.market_brain_cli --snapshot examples/market-brains/swing-synthetic.snapshot.json --portfolio examples/portfolio-insider/bnb-dca-negative.input.json --out /tmp/three.json
python3 -m unittest discover -s tests
```

Giữ snapshot cùng ruleset và revision mã nguồn để tái tính. Tự sửa dữ liệu rồi
băm lại không tạo bằng chứng xác thực. Ví dụ synthetic được ghi nhãn riêng; file
BNB observed là lượt thu thập tại cutoff được lưu, không phải dữ liệu mới mỗi khi
mở. Không có kết luận đảm bảo lợi nhuận hoặc tác vụ thực thi.
