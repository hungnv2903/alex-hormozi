# /// script
# dependencies = [
#   "google-genai",
# ]
# ///
import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print(f"{'TÊN MODEL (DÙNG TRONG CODE)':<35} | {'TÊN HIỂN THỊ'}")
print("-" * 75)

for m in client.models.list():
    actions = m.supported_actions or []
    if "generateContent" in actions:
        model_id = m.name.replace("models/", "")
        display_name = getattr(m, "display_name", "") or ""
        print(f"{model_id:<35} | {display_name}")