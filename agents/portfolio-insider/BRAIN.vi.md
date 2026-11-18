# Bộ não Portfolio Insider — phiên bản 1

## Mục đích

Hiểu hiện trạng danh mục, thử một quyết định, giải thích giới hạn rủi ro trước khi
người dùng tự hành động. Không đặt lệnh. Không lấy quy mô tài sản làm thước đo an
toàn: phân tích tỷ lệ trên NAV, giá vốn và ngân sách người dùng tự chọn.

## 1. Hiện trạng trước quyết định

Hiển thị NAV, USD/stablecoin và tiền khả dụng theo tỷ lệ; từng tài sản có lượng,
giá hiện tại, vốn còn nằm trong lượng đang giữ, giá vốn bình quân, PnL chưa thực
hiện theo tiền và % giá vốn. Không biết giá vốn thì ghi thiếu dữ liệu, không coi
là bằng 0. Phân biệt lãi đã thực hiện (chưa hỗ trợ đối soát sổ giao dịch) và lãi
chưa thực hiện từ snapshot. Đồng stablecoin cần tỷ giá rõ ràng.

DCA âm/dương được xét theo giá hiện tại so với giá vốn cũ. Giảm giá vốn không làm
khoản lỗ cũ biến mất. Lãi đang có cũng có thể mất đi. Cùng lượng, tiền mặt và giá
hiện tại thì rủi ro giảm NAV tương lai giống nhau dù giá vốn khác nhau.

## 2. Hai giới hạn, hai cơ sở tính

**Lần quyết định:** B = khoản dự kiến ban đầu × tỷ lệ chịu lỗ của lần quyết định.
Đóng băng B trước khi thu nhỏ khoản mua; không tính lại B từ khoản đã thu nhỏ.
Có thể phân bổ B nhỏ hơn bằng allocated_loss_budget. Không tự tái sử dụng cùng
ngân sách qua nhiều lệnh; phiên bản snapshot chưa quản lý ngân sách liên phiên.

**Chu kỳ:** F = NAV mốc đã chốt × (1 − tỷ lệ chịu lỗ chu kỳ).
Toàn danh mục trong kịch bản sau quyết định phải còn NAV ≥ F. Mốc không tự đổi
sau DCA hoặc sau khi lỗ; nạp/rút phải được đối soát trước. Mốc hiện do người dùng
cung cấp, chưa có lưu trữ bất biến hay cơ chế chống sửa mốc.

Với giá vào E, giá bất lợi S của lần quyết định, giá chu kỳ C, khoản mua/notional
x, hệ số chi phí giả định b và hướng d = +1 long/spot, −1 short:

- Lỗ chân mới = x × d(E−S)/E + bx ≤ B.
- NAV chu kỳ sau mua = NAV kịch bản danh mục cũ − x × d(E−C)/E − bx ≥ F.
- x còn phải ≤ khoản user muốn mua và giới hạn tiền/margin khả dụng.

Đây là nhiều **cận trên**, không phải ép một khoản đầu tư tối thiểu. x có thể
bằng 0. Giá bất lợi phải thực sự nằm phía lỗ; phần thu nhỏ làm tròn xuống 0,01
đơn vị tiền báo cáo. Bộ não không tự gắn xác suất vào kịch bản.

## 3. Ví dụ BNB: giữ nguyên cả giá vốn lẫn PnL

Snapshot giả lập: 700 USD tiền mặt + 0,5 BNB giá 600 USD = NAV 1.000 USD.
Vốn BNB đang giữ 400 USD, giá vốn 800 USD, PnL −100 USD (−25%).
Muốn mua 100 USD; chịu lỗ lần này 10% khoản dự kiến = 10 USD.
Kịch bản tháng giá 500 USD; chu kỳ giá 300 USD. NAV mốc 1.000 USD, chịu giảm
20%, nên sàn NAV chu kỳ là 800 USD. Chưa tính phí.

- Cận lần quyết định: 10 / ((600−500)/600) = **60 USD**.
- Danh mục cũ ở giá 300 còn 850 USD; dư 50 USD trên sàn NAV.
  Cận chu kỳ: 50 / ((600−300)/600) = **100 USD**.
- Cận cuối: min(100 muốn mua, 60, 100, tiền khả dụng) = **60 USD**.

| Chỉ số | Hiện tại | Sau mua 60 USD |
|---|---:|---:|
| Lượng BNB | 0,5 | 0,6 |
| Tiền mặt | 700 | 640 |
| Vốn BNB | 400 | 460 |
| Giá vốn bình quân | 800 | 766,67 |
| PnL ngay tại giá 600 | −100 | −100 |
| NAV nếu giá về 500 | 950 | 940 |
| PnL BNB nếu giá về 500 | −150 | −160 |
| NAV chu kỳ nếu giá về 300 | 850 | 820 |
| PnL BNB nếu giá về 300 | −250 | −280 |

Lỗ chân mới ở 500 là 10 USD; toàn danh mục giảm 60 USD từ NAV hiện tại, vì lượng
BNB cũ cũng giảm. PnL −280 ở giá 300 khác với giảm NAV 180 từ mốc 1.000.

Nếu vốn BNB cũ chỉ 200 USD (giá vốn 400), hiện đang lời 100: mua cùng 60 USD cho
giá vốn mới 433,33; NAV chu kỳ vẫn 820 nhưng PnL BNB là −80. Nhờ vậy bộ não thấy
được DCA dương/âm mà không đánh tráo rủi ro tương lai với lịch sử giá vốn.

## 4. Futures

Áp dụng cho hợp đồng tuyến tính long/short. Ngân sách chịu lỗ gắn với khoảng cách
giá vào–SL dự kiến để tìm quantity/notional. Đòn bẩy thay đổi margin ước tính,
không thay đổi lỗ theo giá của cùng quantity. Futures wallet + PnL đóng góp NAV;
không cộng cả giá trị danh nghĩa vị thế vào NAV. Các tài khoản phải tách khỏi tiền
spot để không đếm trùng.

SL là giá dùng tính toán; không đồng nghĩa có lệnh SL trên sàn hoặc lỗ thực tế
được đảm bảo ở đó. Chưa tính thanh lý, funding, trượt giá, cơ chế margin riêng của
sàn: báo cáo luôn để an toàn margin/thanh lý ở trạng thái chưa xác minh. Options
và inverse chưa hỗ trợ, không được suy diễn bằng công thức tuyến tính.

## 5. Đường vào dữ liệu và ba agent

User chọn danh mục/tài sản, nhu cầu và thời gian giữ. Miễn phí ưu tiên nhập tay;
CSV và kết nối chỉ đọc là giai đoạn sau. Chưa lấy dữ liệu tài khoản thật.
Portfolio Insider đề xuất phạm vi: tích lũy chu kỳ tháng/tuần/ngày; swing
ngày/H4/H1; ngắn hạn H4/H1/M15. Chỉ phân tích tài sản đang giữ hoặc được yêu cầu,
không quét tất cả thị trường. Các vị thế khác vẫn phải tham gia kịch bản NAV.

Wyckoff và SMC chạy độc lập trên cùng snapshot hợp lệ. Bộ não kiểm tra phạm vi,
độ mới và hash khi nhận evidence; hash không chứng minh nguồn thật. Chưa tự gọi
pipeline từ bộ não; runner cũ hiện phân tích H4/H1, chưa hỗ trợ đầy đủ mọi profile.
Mâu thuẫn, thiếu hoặc lỗi dữ liệu phải hiển thị, không ép thành TRUE. Nhận định
thị trường không đồng nghĩa xác suất đã được hiệu chuẩn.

## 6. TapeOut và đầu ra

Bộ tính offchain chuẩn bị đầu vào. Mục tiêu thiết kế mạch: so sánh lỗ với B, NAV
kịch bản với F, rồi ghép các điều kiện công khai có tín hiệu hợp lệ dữ liệu.
Hiện trả NOT_REQUESTED, circuit_id=null; chưa triển khai mạch Decision Check.
Chưa được nói mạch xác minh toàn bộ phân tích hay tính đúng của dữ liệu tài khoản.

Báo cáo có hiện trạng, hợp đồng rủi ro/mốc, các cận, phương án giữ nguyên, khoản
user yêu cầu, khoản giới hạn, PnL sau DCA, evidence và mã lý do. Giữ cùng input,
phiên bản mã và SHA-256 để chạy lại. Người dùng thay đổi khoản dự kiến là tạo
một phương án mới với ngân sách mới; so sánh không sửa báo cáo gốc.

## 7. Phạm vi hoàn thành

Đã có module Python, CLI, ví dụ giả lập và kiểm thử. Chưa gắn bộ não này vào UI,
API hosted, private account sync hay TapeOut mainnet. Bước tiếp theo là adapter
snapshot/evidence chung, lời giải giao diện và lưu lịch sử mốc/ngân sách nhất quán.
