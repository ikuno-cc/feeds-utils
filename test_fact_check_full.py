import json
from app.services.fact_checker import fact_check

with open("test_claims.json", encoding="utf-8") as f:
    claims = json.load(f)

with open("test_articles.json", encoding="utf-8") as f:
    articles = json.load(f)

result = fact_check(claims, articles, threshold=0.25)
print(f"Verified {len(result)} of {len(claims)} claims")
for c in result:
    print(f"  - {c['claim']}")
