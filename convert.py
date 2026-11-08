import pathlib
import pymupdf4llm

input_pdf = "100M-LEADS-Alex-Hormozi_en.pdf"
output_md = "100M-LEADS-Alex-Hormozi_en.md"

print(f"Đang trích xuất nội dung từ '{input_pdf}'...")
md_content = pymupdf4llm.to_markdown(input_pdf)

pathlib.Path(output_md).write_text(md_content, encoding="utf-8")
print(f"Hoàn thành! Đã tạo file '{output_md}' thành công.")