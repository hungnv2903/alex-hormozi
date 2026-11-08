# /// script
# dependencies = [
#   "google-genai",
# ]
# ///
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

PROMPT_TRANSCREATION = """
Bạn là một chuyên gia bản địa hóa tài liệu Kinh doanh & Marketing cao cấp (Transcreator & Senior Copywriter).
Nhiệm vụ của bạn là dịch tài liệu Markdown sau từ tiếng Anh sang tiếng Việt theo quy trình 3 giai đoạn:

1. PHÂN TÍCH THUẬT NGỮ:
   - Các thuật ngữ chuẩn ngành quốc tế không nên dịch gượng gạo (giữ nguyên hoặc chú thích mở ngoặc lần đầu): ROI, CAC, LTV, Lead Generation, B2B/B2C, Funnel, Value Proposition, Product-Market Fit.
   - Các thuật ngữ kinh doanh thông dụng cần dịch chuẩn xác, gãy gọn: "revenue streams" (dòng doanh thu), "operational efficiency" (hiệu quả vận hành), "leverage" (tận dụng/đòn bẩy).

2. BẢN ĐỊA HÓA VĂN PHONG (THUẦN VIỆT & TRÔI CHẢY):
   - Không dịch word-by-word (từ nối từ). Tái cấu trúc câu theo tư duy ngữ pháp tiếng Việt: chủ động, mạch lạc, nhấn mạnh hành động và kết quả.
   - Giữ nguyên văn phong truyền cảm hứng, thuyết phục của tác giả nguyên bản.

3. ĐỊNH DẠNG:
   - Giữ nguyên cấu trúc Markdown (tiêu đề #, ##, danh sách gạch đầu dòng, bảng biểu, in đậm).

Văn bản gốc cần dịch:
\"\"\"{source_text}\"\"\"

Hãy trả về bản dịch tiếng Việt hoàn chỉnh, chỉn chu nhất:
"""

def translate_document(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Nhờ context window lớn (1M-2M tokens) của Gemini, có thể gửi cả tài liệu dài trong 1 lần gọi
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=PROMPT_TRANSCREATION.format(source_text=content),
        config=types.GenerateContentConfig(
            temperature=0.3, # Giữ nhiệt độ thấp để bản dịch bám sát ý tưởng gốc và ổn định
        )
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Đã dịch thành công và lưu tại: {output_path}")

if __name__ == "__main__":
    translate_document("100M-OFFERS-Alex-Hormozi_en.md", "100M-OFFERS-Alex-Hormozi_vi.md")