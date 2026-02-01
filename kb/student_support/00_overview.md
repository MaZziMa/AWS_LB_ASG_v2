# Knowledge Base: Hỗ trợ sinh viên & tuyển sinh (HUTECH) — Tổng quan

## Phạm vi
Tài liệu này dùng cho trợ lý AI hỗ trợ:
- Tư vấn tuyển sinh (ngành, phương thức xét tuyển, hồ sơ, mốc thời gian)
- Giải đáp học phí/học bổng (nguyên tắc chung, lưu ý)
- Hỗ trợ sinh viên (dịch vụ, thủ tục phổ biến, kênh liên hệ)

## Nguyên tắc trả lời
- Nếu câu hỏi cần số liệu theo ngành/đợt cụ thể (học phí ngành X, deadline đợt Y, link đăng ký) → ưu tiên gọi tool/nguồn dữ liệu có cấu trúc.
- Nếu câu hỏi là quy định/FAQ/hướng dẫn thủ tục → tra Knowledge Base.
- Nếu thông tin trong KB không đủ chắc chắn → hướng dẫn liên hệ kênh chính thức.

## Chính sách độ chính xác (rất quan trọng)

KB này ưu tiên trả lời theo **quy trình/hướng dẫn** và các “nguyên tắc chung”.

Các thông tin sau **không nên suy đoán** nếu KB không có hoặc không cập nhật:
- Học phí cụ thể theo ngành/năm.
- Mốc deadline theo từng đợt.
- Điều kiện học bổng chi tiết theo từng năm.

Khi gặp các câu hỏi dạng trên, agent nên:
- Gọi tool/nguồn dữ liệu có cấu trúc (nếu có), hoặc
- Trả lời theo nguyên tắc + hướng dẫn kênh chính thức.

## Điều phối (routing) theo intent

| Intent | Ví dụ | Nguồn ưu tiên |
|---|---|---|
| Tuyển sinh - thủ tục | "Xét học bạ cần giấy tờ gì?" | KB |
| Tuyển sinh - học phí/deadline theo ngành | "AI 2026 học phí?" | Tool → nếu không có thì KB nguyên tắc + liên hệ |
| Sinh viên - học vụ | "Đăng ký môn/đổi lớp thế nào?" | KB |
| Sinh viên - giấy tờ | "Xin giấy xác nhận SV/bảng điểm?" | KB |
| Sinh viên - IT/tài khoản | "Quên mật khẩu email/portal?" | KB |
| Khẩn cấp/ngoại lệ | "Mất thẻ SV/đóng sai học phí" | KB + liên hệ |

## Kênh liên hệ (tham chiếu)
- Hotline tuyển sinh: 028 5445 5555
- Email tuyển sinh: tuyensinh@hutech.edu.vn

> Gợi ý vận hành KB: mỗi khi phát sinh câu hỏi mới mà agent trả lời chưa tốt, bổ sung 1 mục vào handbook tương ứng (hoặc tạo file mới theo topic).
