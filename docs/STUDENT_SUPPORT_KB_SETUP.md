# Student Support + Admissions: Bedrock Knowledge Base (KB)

Mục tiêu: tạo một KB để agent trả lời các câu hỏi dạng FAQ/quy định/hướng dẫn thủ tục; còn dữ liệu “chuẩn theo ngành/đợt” (học phí, deadline, link đăng ký) nên lấy từ tool (DynamoDB/Lambda) để tránh sai.

## 1) Nội dung KB
- Nằm trong thư mục: kb/student_support/
- Khuyến nghị tách theo chủ đề (admissions, tuition, services, contacts…)

## 2) Tạo S3 bucket và upload KB docs
Bạn có thể dùng script PowerShell: scripts/kb/upload_student_support_kb.ps1

## 3) Tạo Knowledge Base trong Bedrock (Console)
1. Bedrock → Knowledge Bases → Create knowledge base
2. Data source: S3 bucket đã upload
3. Chọn embedding model + vector store theo hướng dẫn console
4. Sync/ingest dữ liệu

## 4) Gắn KB vào Agent
Trong Bedrock Agent:
- Add/Enable Knowledge Base
- Set retrieval behavior theo nhu cầu (ưu tiên retrieve cho FAQ)

## 5) Quy tắc điều phối (KB vs Tools)
- Câu hỏi cần số liệu chính xác theo ngành/đợt: gọi tool.
- Câu hỏi giải thích/chính sách/FAQ: retrieve từ KB.

## 6) Use case mẫu
- "Học phí ngành AI năm 2026 bao nhiêu?" → tool
- "Xét học bạ cần chuẩn bị những giấy tờ gì?" → KB
