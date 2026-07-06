import os
import json
import requests
from .base import BaseAIProvider

class GroqProvider(BaseAIProvider):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        
        # 💡 .env から指定モデルを取得
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        
        # ⚠️ 【廃止モデル自動救済ガード】
        # もし .env に廃止済みの「specdec」モデルが残っていた場合、自動的に「versatile」に修正して通信エラーを防ぎます。
        if "specdec" in model_name:
            print(f"🔄 [Groqシステム警告] 廃止されたモデル名 '{model_name}' を検知しました。自動的に稼働中の最新推奨モデル 'llama-3.3-70b-versatile' に切り替えて通信します。")
            model_name = "llama-3.3-70b-versatile"
            
        self.model = model_name
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def ask_assignment(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful assistant designed to output JSON. You must return a valid JSON object."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        response = requests.post(self.url, headers=headers, json=payload, timeout=30)
        
        # エラー発生時のデバッグ出力
        if response.status_code != 200:
            try:
                error_json = response.json()
                error_msg = error_json.get("error", {}).get("message", "Unknown error")
                error_type = error_json.get("error", {}).get("type", "Unknown type")
                print(f"\n⚠️ [Groq API Error Detail]")
                print(f"  Status Code: {response.status_code}")
                print(f"  Error Type : {error_type}")
                print(f"  Message    : {error_msg}\n")
            except Exception:
                print(f"\n⚠️ [Groq API Raw Error Response]")
                print(f"  Status Code: {response.status_code}")
                print(f"  Response   : {response.text}\n")
                
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]