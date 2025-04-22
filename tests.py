import requests

details = requests.get("http://localhost:8000/api/anime/details?source=allanime&id=dqvMzB6h9MQA5XJEz")
#print(detai)
url_payload = details.json()["episodes"][0]["url"]

sources = requests.get(f"http://localhost:8000/api/anime/get-episode?source=allanime&id={url_payload}")

print(sources.json())