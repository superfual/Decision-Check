# Portfolio Insider Agent — Định danh và phạm vi

Đây là nhánh ươm tạo ý tưởng trong Decision Check, chưa triển khai agent hay kết nối tài khoản.

Portfolio Insider phân tích theo yêu cầu của người dùng khi được cung cấp dữ liệu hoặc cấp quyền chỉ đọc. Phạm vi gồm Spot, Futures và Options; không chỉ danh mục hold coin.

Agent tìm mức tập trung rủi ro, rủi ro tổng hợp xuyên nhiều sản phẩm, vai trò phòng hộ, chất lượng DCA, nguồn tạo lãi/lỗ và tác động của các kịch bản. Nhận định cần gắn với số liệu và giới hạn dữ liệu, không suy đoán lịch sử hành vi từ một ảnh chụp số dư.

Bộ tính toán chuyên biệt chịu trách nhiệm về số; agent giải thích ý nghĩa. Spot, Futures tuyến tính/nghịch đảo và Options cần cách tính riêng. Ký quỹ, thanh lý và Greeks phụ thuộc sản phẩm, sàn và mô hình.

Không đặt/sửa/hủy/đóng lệnh, đổi đòn bẩy/ký quỹ hay chuyển tài sản. Không cần quyền giao dịch hoặc rút tiền.

Vai trò trong Decision Check:
- Wyckoff–SMC: bối cảnh và bằng chứng thị trường.
- Portfolio Insider: tình trạng, mức phơi nhiễm và khả năng chịu rủi ro của người dùng.
- TapeOut dự kiến: kiểm tra điều kiện định lượng được mã hóa, không xác thực toàn bộ suy luận của agent.

Ví dụ giả định: BTC Spot + BTC Long Futures + BTC Call có thể cùng tăng mức đặt cược vào chiều tăng. Ngược lại một lệnh Short có thể đang phòng hộ cho Spot. Phải nhìn tổng thể, không đánh giá từng sản phẩm riêng rẽ.

Site hiện tại vẫn chỉ là bộ tính Spot minh họa, chưa phải Portfolio Insider hoàn chỉnh. Sau này sẽ mở repo riêng để xây kỹ adapter dữ liệu, kế toán, mô hình rủi ro, agent và kiểm thử.

Xem [đặc tả đầy đủ](README.md).
