import requests

url = "https://coinshares.com/us/etf/brrr/"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

resp = requests.get(url, headers=headers, timeout=20)
print("Status code:", resp.status_code)
print("Response length:", len(resp.text))
print("Contains 'XBTUSD'?", "XBTUSD" in resp.text)
print("Contains 'BITCOIN'?", "BITCOIN" in resp.text)
print("Contains 'Holdings'?", "Holdings" in resp.text)

# Save the raw HTML so we can inspect it if needed
with open("brrr_debug.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("\nSaved raw response to brrr_debug.html -- open it and search for 'XBTUSD' to confirm.")