# /// script
# dependencies = [
#   "google-genai",
# ]
# ///
import os
import re
import sys
import time
from pathlib import Path
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT_TRANSCREATION = """
Bạn là một chuyên gia bản địa hóa tài liệu Kinh doanh & Marketing cao cấp (Transcreator & Senior Copywriter).
Nhiệm vụ của bạn là dịch đoạn trích sau từ cuốn sách của Alex Hormozi sang tiếng Việt.

YÊU CẦU DỊCH THUẬT:
1. THUẬT NGỮ CHUYÊN NGÀNH:
   - Giữ nguyên các thuật ngữ cốt lõi quốc tế (mở ngoặc chú thích nếu cần): Core Offer, Leads, Lead Magnet, Cold Outreach, Warm Outreach, Paid Ads, Content, Affiliates, Agency, CAC, LTV, ROI, Funnel, Hook, Retargeting.
   - Các từ thông dụng dịch thoát ý, gãy gọn, giàu tính hành động.

2. VĂN PHONG (THUẦN VIỆT, ĐẦY NĂNG LƯỢNG):
   - Alex Hormozi viết với văn phong thẳng thắn, thực chiến, ngắn gọn và giàu tính hành động. Tránh tuyệt đối dịch kiểu "word-by-word" rườm rà.
   - Hành văn mạch lạc, tự nhiên như một cuốn sách kinh doanh xuất bản chính thức tại Việt Nam.

3. ĐỊNH DẠNG:
   - Giữ nguyên toàn bộ cấu trúc Markdown (tiêu đề #, ##, danh sách, bảng biểu, in đậm).

Đoạn văn bản gốc:
\"\"\"{source_text}\"\"\"

Bản dịch tiếng Việt hoàn chỉnh:
"""

def split_content_safely(content: str, max_chunk_chars: int = 7000):
    """
    Tách tài liệu an toàn:
    1. Ưu tiên tách theo tiêu đề Markdown (#, ##, ###).
    2. Nếu một đoạn vẫn vượt quá max_chunk_chars, tự động chia nhỏ tiếp theo đoạn văn (\n\n).
    """
    initial_splits = re.split(r'(?=\n#{1,3}\s)', content)
    refined_splits = []

    for block in initial_splits:
        if len(block) <= max_chunk_chars:
            refined_splits.append(block)
        else:
            paragraphs = block.split("\n\n")
            sub_block = ""
            for p in paragraphs:
                if len(sub_block) + len(p) + 2 < max_chunk_chars:
                    sub_block += (p + "\n\n")
                else:
                    if sub_block:
                        refined_splits.append(sub_block)
                    sub_block = p + "\n\n"
            if sub_block:
                refined_splits.append(sub_block)

    # Gộp các đoạn nhỏ lại với nhau cho tối ưu token
    final_chunks = []
    current_chunk = ""
    for piece in refined_splits:
        if not piece.strip():
            continue
        if len(current_chunk) + len(piece) < max_chunk_chars:
            current_chunk += piece
        else:
            if current_chunk:
                final_chunks.append(current_chunk)
            current_chunk = piece
    if current_chunk:
        final_chunks.append(current_chunk)

    return final_chunks

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
            wait_time = attempt * 8
            print(f" [Lỗi ({type(e).__name__}), thử lại lần {attempt}/{max_retries} sau {wait_time}s...] ", end="", flush=True)
            time.sleep(wait_time)

def process_translation(input_file: str, output_file: str, target_chunk: int = None):
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Lỗi: Không tìm thấy file '{input_file}'")
        return

    # Tự động tạo thư mục cache riêng biệt theo tên file đầu vào
    cache_dir = Path(f"cache_{input_path.stem}")
    cache_dir.mkdir(exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    chunks = split_content_safely(content)
    total = len(chunks)
    print(f"Tài liệu: {input_file} | Tổng số phần cần dịch: {total}")
    print(f"Thư mục lưu cache: {cache_dir.name}/\n")

    # Trường hợp dịch lại 1 chunk cụ thể
    if target_chunk is not None:
        if target_chunk < 1 or target_chunk > total:
            print(f"Lỗi: Số thứ tự chunk hợp lệ từ 1 đến {total}")
            return
        chunk_file = cache_dir / f"chunk_{target_chunk:03d}.md"
        print(f"Đang dịch lại riêng chunk [{target_chunk}/{total}]...", end="", flush=True)
        try:
            res = translate_chunk_with_retry(chunks[target_chunk - 1])
            chunk_file.write_text(res, encoding="utf-8")
            print(" -> Đã cập nhật xong.")
        except Exception as e:
            print(f"\nLỗi: {e}")
            return
    else:
        # Dịch tuần tự các chunk
        for idx, chunk in enumerate(chunks, 1):
            chunk_file = cache_dir / f"chunk_{idx:03d}.md"

            if chunk_file.exists() and chunk_file.stat().st_size > 0:
                print(f"[{idx}/{total}] Đã có trong cache -> Bỏ qua.")
                continue

            print(f"[{idx}/{total}] Đang dịch...", end="", flush=True)
            try:
                translated_text = translate_chunk_with_retry(chunk)
                chunk_file.write_text(translated_text, encoding="utf-8")
                print(" -> Xong.")
                time.sleep(2)
            except Exception as e:
                print(f"\nKhông thể hoàn tất phần {idx}: {e}")
                print("Bạn có thể chạy lại lệnh để tiếp tục từ phần này.")
                return

    # Tổng hợp toàn bộ các chunk đã dịch thành file hoàn chỉnh
    print("\nĐang tổng hợp thành tài liệu hoàn chỉnh...")
    with open(output_file, "w", encoding="utf-8") as outfile:
        for idx in range(1, total + 1):
            chunk_file = cache_dir / f"chunk_{idx:03d}.md"
            if chunk_file.exists():
                outfile.write(chunk_file.read_text(encoding="utf-8") + "\n\n")

    print(f"Hoàn thành xuất sắc 100%! Bản dịch lưu tại: {output_file}")

if __name__ == "__main__":
    # Nhận tên file từ tham số dòng lệnh hoặc dùng mặc định
    in_file = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "100M-LEADS-Alex-Hormozi_en.md"
    out_file = in_file.replace("_en.md", "_vi.md")
    if out_file == in_file:
        out_file = f"{Path(in_file).stem}_vi.md"

    # Kiểm tra xem có truyền cờ dịch lại 1 chunk không
    re_chunk = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        re_chunk = int(sys.argv[1])
    elif len(sys.argv) > 2 and sys.argv[2].isdigit():
        re_chunk = int(sys.argv[2])

    process_translation(in_file, out_file, re_chunk)