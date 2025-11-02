import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
import openai

# Tải các biến môi trường từ file .env
load_dotenv()

# --- Cấu hình cho Google Gemini ---
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_API_KEY = 'vanducngo'
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

    print("--- Các model có sẵn ---")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
        print("-------------------------")

    # gemini_model = genai.GenerativeModel('gemini-pro')
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("CẢNH BÁO: GOOGLE_API_KEY không được tìm thấy trong file .env")
    gemini_model = None

# --- Cấu hình cho OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("CẢNH BÁO: OPENAI_API_KEY không được tìm thấy trong file .env")


def call_gemini_api(prompt: str) -> str:
    """
    Gửi một prompt đến Google Gemini API và trả về kết quả dạng text.
    Bao gồm xử lý lỗi cơ bản và thử lại.
    """
    if not gemini_model:
        raise ValueError("Gemini API key chưa được cấu hình.")
    
    retries = 3
    for i in range(retries):
        try:
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Lỗi khi gọi Gemini API (lần {i+1}/{retries}): {e}")
            if i < retries - 1:
                print("Đang thử lại sau 5 giây...")
                time.sleep(5)
            else:
                print("Không thể kết nối đến Gemini API sau nhiều lần thử.")
                raise  # Ném lại lỗi sau khi đã thử hết số lần

def call_openai_api(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """
    Gửi một prompt đến OpenAI API (ChatCompletion) và trả về kết quả dạng text.
    Bao gồm xử lý lỗi cơ bản và thử lại.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key chưa được cấu hình.")

    retries = 3
    for i in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful legal assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            print(f"Lỗi khi gọi OpenAI API (lần {i+1}/{retries}): {e}")
            if i < retries - 1:
                print("Đang thử lại sau 5 giây...")
                time.sleep(5)
            else:
                print("Không thể kết nối đến OpenAI API sau nhiều lần thử.")
                raise

# Test file này một cách độc lập
if __name__ == '__main__':
    test_prompt = "Luật đất đai 2024 có hiệu lực khi nào?"
    
    # Test Gemini
    if gemini_model:
        try:
            print("--- Testing Gemini ---")
            gemini_response = call_gemini_api(test_prompt)
            print(f"Gemini response: {gemini_response}")
        except Exception as e:
            print(f"Lỗi test Gemini: {e}")

    # Test OpenAI
    if OPENAI_API_KEY:
        try:
            print("\n--- Testing OpenAI (gpt-3.5-turbo) ---")
            openai_response = call_openai_api(test_prompt)
            print(f"OpenAI response: {openai_response}")
        except Exception as e:
            print(f"Lỗi test OpenAI: {e}")