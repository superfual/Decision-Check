# Nội dung sản phẩm theo luồng hiện tại

Hiểu danh mục trước. Kiểm tra cơ hội sau.

01 · Portfolio Insider Agent
Bạn mô tả coin/token, stablecoin và vị thế Futures đang giữ, rồi chọn kế hoạch tiếp theo. Agent tính NAV, tỷ trọng, giá vốn bình quân, PnL chưa thực hiện và hai giới hạn rủi ro. Tài sản muốn đầu tư có thể chưa nằm trong danh mục.

02A · Wyckoff Agent
Sau khi hoàn thành Portfolio Insider, Agent phân tích bối cảnh giá và khối lượng của tài sản trong kế hoạch. Nó kiểm tra trading range, thứ tự sự kiện và điều kiện xác nhận theo khung thời gian đã chọn; thiếu bằng chứng thì không ép thành TRUE.

02B · SMC Agent
Chạy độc lập với Wyckoff trên cùng bộ dữ liệu đã kiểm tra. Agent tìm cấu trúc giá, quét thanh khoản và vùng giá còn hiệu lực. Thiên hướng tăng/giảm được phân biệt với việc đã đáp ứng đầy đủ điều kiện của một thiết lập.

Tôi bắt đầu từ đâu?
Bấm Portfolio Insider Agent, mô tả danh mục và kế hoạch, rồi chọn “Phân tích kế hoạch”. Bước 03 sẽ mở nút tiếp tục sang Wyckoff–SMC với đúng tài sản, loại sản phẩm và khung thời gian vừa chọn. Hai tab thị trường ở trang chính thể hiện quy trình, không phải lối chạy riêng trước khi có danh mục.

Đang giữ OKB và USDT, tôi có thể kiểm tra mua BNB không?
Có. Danh mục hiện tại và tài sản trong kế hoạch là hai phần riêng. Portfolio Insider vẫn tính rủi ro của toàn bộ tài sản/vị thế đang giữ, đồng thời xem khoản BNB mới ảnh hưởng thế nào đến tiền khả dụng và ngưỡng chịu lỗ. Wyckoff và SMC phân tích tài sản của kế hoạch; không tự quét tất cả coin.

Dữ liệu cho Wyckoff và SMC đến từ đâu?
Bước phân tích thị trường lấy dữ liệu công khai từ Binance theo sản phẩm Spot hoặc USD-M Futures trong kế hoạch. Chỉ phân tích sau khi kiểm tra nến đã đóng, đủ lịch sử, đúng khoảng thời gian và không bị trùng hoặc thiếu. Tích lũy theo chu kỳ dùng tháng/tuần/ngày; swing dùng ngày/H4/H1; ngắn hạn dùng H4/H1/M15. Nếu nguồn bị chặn hoặc thiếu lịch sử, hệ thống báo chưa đủ dữ liệu, không tự đổi sàn hay đổi Futures sang Spot. Adapter cho sàn khác chưa được hỗ trợ.

Giá vốn, PnL và mức chịu lỗ được hiểu thế nào?
PnL chưa thực hiện của Spot = số lượng đang giữ × (hiện giá − giá vốn bình quân). Futures tuyến tính tính theo entry và chiều long/short. Mức lỗ chấp nhận của từng tài sản được nhập theo % giá vốn/entry; hệ thống đổi ra mức giá tương ứng. Ký quỹ không bị cộng trùng vào NAV. Đây là phân tích số dư bạn nhập, chưa phải đối soát đầy đủ giao dịch, phí và funding; không có lệnh cắt lỗ nào được đặt.

Hai giới hạn rủi ro khác nhau thế nào?
Giới hạn lần quyết định tính từ khoản dự kiến đầu tư ban đầu và tỷ lệ lỗ chấp nhận cho lần đó. Giới hạn chu kỳ tính từ NAV mốc đã chọn và toàn danh mục sau phương án. Hai phép kiểm tra cùng giới hạn khoản đầu tư; mốc không tự đổi khi DCA hoặc khi đang lỗ. Giảm giá vốn không làm khoản lỗ cũ biến mất.

Ba Agent phối hợp ra sao?
Portfolio Insider xác định tình trạng danh mục và phạm vi kế hoạch trước. Wyckoff và SMC nhận cùng snapshot nhưng không lấy kết luận của nhau làm đầu vào. Phần đối chiếu sau đó ghép điều kiện thị trường với giới hạn danh mục của khoản user yêu cầu. Mỗi nhánh có trạng thái hợp lệ và đạt/chưa đạt; thiếu dữ liệu hoặc lệch phạm vi thì chưa thể kết luận. Futures vẫn chưa được xác nhận an toàn về margin và thanh lý.

TapeOut hiện tham gia ở mức nào?
Hiện đã có mô phỏng logic ghép ba nhánh và kiểm thử đủ 64 tổ hợp của sáu bit hợp lệ/đạt. Đây là phép kiểm tra cục bộ, chưa phải mạch đã triển khai trên TapeOut. Bước tiếp theo là chốt quy tắc, chuẩn hóa số và giới hạn bit, xây mạch so sánh ngân sách lỗ và sàn NAV, đo chi phí rồi kiểm chứng. Không gọi kết quả hiện tại là bằng chứng onchain.

X Layer sẽ ghi nhận điều gì?
Hướng dự kiến là triển khai mạch Decision Check và ghi nhận tham chiếu cần thiết trên X Layer sau khi thiết kế được kiểm chứng. Bản ghi sẽ phân biệt đầu vào, phiên bản quy tắc, danh tính mạch và khối đọc/giao dịch nếu có. Hiện Decision Check chưa triển khai mạch mới hoặc gửi giao dịch từ luồng này; không đưa toàn bộ danh mục cá nhân lên blockchain.

Tôi có thể kiểm tra lại kết quả không?
Bạn có thể xuất bản ghi JSON gồm đầu vào và báo cáo. Khi giữ cùng dữ liệu và phiên bản mã/quy tắc, có thể chạy lại để đối chiếu. Đổi khoản đầu tư là thử một phương án mới, không sửa kết quả cũ. Hash giúp nhận diện dữ liệu, không tự chứng minh dữ liệu tài khoản đầy đủ hay nhận định thị trường đúng.

Chúng ta phát triển tiếp phần nào?
Hoàn thiện lời giải của ba Agent và thử nhiều tình huống thực tế; cải thiện phạm vi dữ liệu và đối chiếu báo cáo; chuẩn hóa đầu vào định lượng để thiết kế, kiểm thử và triển khai mạch TapeOut trên X Layer. Việc đồng bộ tài khoản riêng tư là bước sau. Sản phẩm hiện tập trung phân tích, không thực thi giao dịch.
