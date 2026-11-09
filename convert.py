# /// script
# dependencies = [
#   "pymupdf4llm",
# ]
# ///
import sys
from pathlib import Path

# Cấu hình UTF-8 cho console trên Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Kiểm tra tham số dòng lệnh
if len(sys.argv) < 2:
    print("Lỗi: Vui lòng cung cấp đường dẫn file PDF.")
    print("Cách dùng: uv run convert.py <duong_dan_file_pdf>")
    sys.exit(1)

input_pdf = Path(sys.argv[1])

if not input_pdf.exists():
    print(f"Lỗi: Không tìm thấy file '{input_pdf}'")
    sys.exit(1)

import pymupdf4llm

output_dir = Path("en")
output_dir.mkdir(parents=True, exist_ok=True)

output_md = output_dir / f"{input_pdf.stem}.md"

print(f"Đang trích xuất nội dung từ '{input_pdf}'...")
md_content = pymupdf4llm.to_markdown(str(input_pdf))

output_md.write_text(md_content, encoding="utf-8")
print(f"Hoàn thành! Đã tạo file '{output_md}' thành công.")
