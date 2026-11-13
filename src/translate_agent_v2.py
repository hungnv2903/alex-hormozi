# /// script
# dependencies = [
#   "google-genai",
# ]
# ///
import os
import re
import time
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import APIError

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CACHE_DIR = Path("chunks_cache_100leads")
PROMPT_TRANSCREATION = """
Bạn là một chuyên gia bản địa hóa tài liệu Kinh doanh & Marketing cao cấp (Transcreator & Senior Copywriter).
Nhiệm vụ của bạn là dịch đoạn trích sau từ cuốn sách "100M Leads" của Alex Hormozi sang tiếng Việt.

YÊU CẦU DỊCH THUẬT:
1. THUẬT NGỮ CHUYÊN NGÀNH:
   - Giữ nguyên các thuật ngữ cốt lõi quốc tế (có thể mở ngoặc chú thích nếu cần): Grand Slam Offer, Value Equation, CAC, LTV, ROI, Lead, Funnel, Niche, B2B/B2C, Upsell, Downsell, Bonuses, Scarcity, Urgency, Guarantees.
   - Các từ thông dụng dịch thoát ý, gãy gọn: "perceived likelihood of achievement" (khả năng đạt được kết cục trong tâm trí khách hàng), "time delay" (độ trễ thời gian), "effort & sacrifice" (công sức và sự đánh đổi).

2. VĂN PHONG (THUẦN VIỆT, ĐẦY NĂNG LƯỢNG):
   - Alex Hormozi viết với văn phong thẳng thắn, thực chiến, ngắn gọn và giàu tính hành động. Tránh tuyệt đối dịch kiểu "word-by-word" rườm rà.
   - Hành văn mạch lạc, tự nhiên như một cuốn sách kinh doanh xuất bản chính thức tại Việt Nam.

3. ĐỊNH DẠNG:
   - Giữ nguyên toàn bộ cấu trúc Markdown (tiêu đề #, ##, danh sách, bảng biểu, in đậm).

Đoạn văn bản gốc:
\"\"\"{source_text}\"\"\"

Bản dịch tiếng Việt hoàn chỉnh:
"""

def split_markdown_by_headings(content: str, max_chunk_chars: int = 12000):
    sections = re.split(r'(?=\n#{1,3}\s)', content)
    chunks = []
    current_chunk = ""

    for sec in sections:
        if len(current_chunk) + len(sec) < max_chunk_chars:
            current_chunk += sec
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sec
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def translate_chunk_with_retry(chunk_text: str, max_retries: int = 5) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=PROMPT_TRANSCREATION.format(source_text=chunk_text),
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )
            return response.text.strip()
        except Exception as e:
            if attempt == max_retries:
                raise e
            wait_time = attempt * 7  # 7s, 14s, 21s, 28s...
            print(f" [Lỗi tạm thời ({type(e).__name__}), thử lại lần {attempt}/{max_retries} sau {wait_time}s...] ", end="", flush=True)
            time.sleep(wait_time)

def translate_book(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        print(f"Lỗi: Không tìm thấy file '{input_path}'")
        return

    CACHE_DIR.mkdir(exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = split_markdown_by_headings(content)
    total = len(chunks)
    print(f"Tổng số phần cần xử lý: {total}")

    for idx, chunk in enumerate(chunks, 1):
        chunk_file = CACHE_DIR / f"chunk_{idx:03d}.md"

        # Kiểm tra nếu phần này đã được dịch thành công trước đó
        if chunk_file.exists() and chunk_file.stat().st_size > 0:
            print(f"[{idx}/{total}] Đã có sẵn trong cache -> Bỏ qua.")
            continue

        print(f"[{idx}/{total}] Đang dịch...", end="", flush=True)
        try:
            translated_text = translate_chunk_with_retry(chunk)
            chunk_file.write_text(translated_text, encoding="utf-8")
            print(" -> Xong.")
            time.sleep(2)  # Khoảng đệm an toàn giữa các request
        except Exception as e:
            print(f"\nKhông thể hoàn tất phần {idx} sau nhiều lần thử: {e}")
            print("Bạn có thể chạy lại lệnh bất kỳ lúc nào để tiếp tục từ phần này.")
            return

    # Ghép nối toàn bộ các phần thành file hoàn chỉnh
    print("\nĐang tổng hợp các phần thành tài liệu hoàn chỉnh...")
    with open(output_path, "w", encoding="utf-8") as outfile:
        for idx in range(1, total + 1):
            chunk_file = CACHE_DIR / f"chunk_{idx:03d}.md"
            if chunk_file.exists():
                outfile.write(chunk_file.read_text(encoding="utf-8") + "\n\n")

    print(f"Hoàn thành xuất sắc 100%! Bản dịch lưu tại: {output_path}")

if __name__ == "__main__":
    translate_book("100M-LEADS-Alex-Hormozi_en.md", "100M-LEADS-Alex-Hormozi_vi.md")