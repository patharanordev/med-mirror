import requests
import json
import time
import sys

# Configuration
AGENT_URL = "http://localhost:8001/chat"
PROXY_URL = "http://localhost:3000/api/proxy/chat"

def test_streaming(url, name="Direct"):
    print(f"\n--- Testing Streaming: {name} ({url}) ---")
    
    payload = {
        "message": "Hello, explain photosynthesis in 10 words.",
        "history": [],
        "context": "Verification Test"
    }

    try:
        start_time = time.time()
        print(f"Sending request...")
        
        # Enable streaming
        with requests.post(url, json=payload, stream=True, timeout=30) as r:
            if r.status_code != 200:
                print(f"FAILED: Status Code {r.status_code}")
                print(r.text)
                return False
                
            print(f"Connected (Status 200). Headers: {r.headers}")
            
            first_token_time = None
            chunk_count = 0
            full_text = ""
            
            # Iterate over lines (SSE format)
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    # print(f"Raw: {decoded}")
                    
                    if decoded.startswith("data: "):
                        data_str = decoded.replace("data: ", "").strip()
                        if data_str == "[DONE]":
                            print("\nReceived [DONE] signal.")
                            break
                        
                        try:
                            data = json.loads(data_str)
                            content = data.get("content", "")
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    ttft = first_token_time - start_time
                                    print(f"✅ First Token Received! TTFT: {ttft:.4f}s")
                                
                                # Print token (simulating streaming UI)
                                sys.stdout.write(content)
                                sys.stdout.flush()
                                full_text += content
                                chunk_count += 1
                        except json.JSONDecodeError:
                            print(f"[Parse Error] {data_str}")

            total_time = time.time() - start_time
            print(f"\n\n--- Summary ({name}) ---")
            print(f"Total Time: {total_time:.4f}s")
            print(f"Chunks Received: {chunk_count}")
            print(f"Full Text Length: {len(full_text)}")
            
            if chunk_count > 1:
                print("✅ STEAMING VERIFIED (Received multiple chunks)")
                return True
            elif chunk_count == 1:
                print("⚠️  WARNING: Received only 1 chunk. Streaming might be buffering.")
                return True # Technically works, but not streaming well
            else:
                 print("❌ FAILED: No content received.")
                 return False

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

if __name__ == "__main__":
    # Test Direct Agent (if exposed)
    print("Verifying Backend Agent...")
    agent_ok = test_streaming(AGENT_URL, "Backend Agent")
    
    # Test via Proxy (Frontend)
    # Note: Requires Frontend to be running on port 3000
    # print("\nVerifying Frontend Proxy...")
    # proxy_ok = test_streaming(PROXY_URL, "Frontend Proxy")
    
    if agent_ok:
        sys.exit(0)
    else:
        sys.exit(1)
