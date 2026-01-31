import requests
import json
import sys

# Configuration
URL = "http://localhost:8001/chat"

def test_stream():
    payload = {
        "message": "สวัสดีครับ ผมเริ่มมีผื่นแดงที่แขน",
        "history": [],
        "context": "Detected: Red rash on left forearm. Probable Dermatitis."
    }
    
    print(f"🔵 Connecting to Agent at {URL}...")
    print(f"📤 Sending: {payload['message']}")
    print(f"ℹ️  Context: {payload['context']}")
    print("-" * 50)

    try:
        with requests.post(URL, json=payload, stream=True) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return

            print("🟢 Agent Response: ", end="", flush=True)
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_content = decoded_line[6:]
                        if data_content == "[DONE]":
                            print("\n\n✅ Stream Complete.")
                            break
                        try:
                            json_data = json.loads(data_content)
                            if "content" in json_data:
                                token = json_data["content"]
                                print(token, end="", flush=True)
                            if "error" in json_data:
                                print(f"\n❌ Stream Error: {json_data['error']}")
                        except json.JSONDecodeError:
                            pass
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect. Is the 'agent' service running? (docker-compose up)")

if __name__ == "__main__":
    test_stream()
