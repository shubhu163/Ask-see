import os
import sys
import json
import requests
from dotenv import load_dotenv


def main():
    load_dotenv()
    token = os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    model = os.getenv("HF_MODEL", "google/flan-t5-small").strip()

    # CLI: python test_hf_inference.py "prompt text" [model]
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one short sentence."
    if len(sys.argv) > 2:
        model = sys.argv[2]

    if not token:
        print("ERROR: HUGGINGFACEHUB_API_TOKEN is missing. Add it to .env or export it.")
        sys.exit(1)

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 128,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }

    print(f"Testing HF Inference API...\nModel: {model}\nPrompt: {prompt}\n")

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        print(f"HTTP {resp.status_code}")
        try:
            data = resp.json()
        except Exception:
            print(resp.text)
            sys.exit(0)

        # Pretty print response
        print(json.dumps(data, indent=2)[:4000])

        # Extract generated_text if present
        if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
            print("\nGenerated:\n" + data[0]["generated_text"]) 
        elif isinstance(data, dict) and "generated_text" in data:
            print("\nGenerated:\n" + str(data["generated_text"]))
        else:
            print("\nNote: No 'generated_text' field found; see raw response above.")
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    main()


