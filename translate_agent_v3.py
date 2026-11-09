# /// script
# dependencies = [
#   "google-genai",
#   "python-dotenv",
# ]
# ///
import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Cấu hình UTF-8 cho console trên Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Tải biến môi trường từ file .env
load_dotenv()

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

def process_translation(input_file: Path | str, output_file: Path | str, target_chunk: int = None):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"Lỗi: Không tìm thấy file '{input_path}'")
        return

    # Tự động tạo thư mục đầu ra nếu chưa tồn tại
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Tự động tạo thư mục cache riêng biệt theo tên file đầu vào
    cache_dir = Path(f"cache_{input_path.stem}")
    cache_dir.mkdir(exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    chunks = split_content_safely(content)
    total = len(chunks)
    print(f"Tài liệu đầu vào: {input_path} | Tổng số phần cần dịch: {total}")
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
    with open(output_path, "w", encoding="utf-8") as outfile:
        for idx in range(1, total + 1):
            chunk_file = cache_dir / f"chunk_{idx:03d}.md"
            if chunk_file.exists():
                outfile.write(chunk_file.read_text(encoding="utf-8") + "\n\n")

    print(f"Hoàn thành xuất sắc 100%! Bản dịch lưu tại: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Lỗi: Vui lòng cung cấp đường dẫn file markdown cần dịch.")
        print("Cách dùng:")
        print("  Dịch toàn bộ file:      uv run translate_agent_v3.py <path_to_md>")
        print("  Dịch lại 1 chunk:       uv run translate_agent_v3.py <path_to_md> <chunk_id>")
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    input_dir = Path("en")
    output_dir = Path("vi")

    # Xác định đường dẫn file đầu vào: kiểm tra trực tiếp hoặc tìm trong thư mục en/
    if raw_path.is_file():
        in_path = raw_path
    elif (input_dir / raw_path.name).is_file():
        in_path = input_dir / raw_path.name
    else:
        in_path = raw_path  # để hàm process_translation báo lỗi không tìm thấy file

    # Xác định chunk_id (nếu có)
    re_chunk = None
    if len(sys.argv) >= 3:
        try:
            re_chunk = int(sys.argv[2])
        except ValueError:
            print(f"Lỗi: chunk_id phải là số nguyên (nhận được: '{sys.argv[2]}')")
            sys.exit(1)

    # Xác định tên file đầu ra trong thư mục vi/
    out_name = in_path.stem
    if out_name.endswith("_en"):
        out_name = out_name[:-3] + "_vi"
    else:
        out_name = f"{out_name}_vi"
    out_path = output_dir / f"{out_name}.md"

    process_translation(in_path, out_path, re_chunk)
