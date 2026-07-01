from app.services.fact_checker import fact_check

claims = [
    {"claim": "West Texas Intermediate settled below $70 a barrel.", "subject": "West Texas Intermediate", "predicate": "settled below", "value": 70.0, "unit": "$/barrel", "period": "friday, june 26", "basis": "u.s. benchmark crude price", "source_sentence": "west texas intermediate, the u.s. benchmark, settled below $70 a barrel on friday, june 26, for the first time since late february, according to cnbc.", "source_id": "68cf95a2-a7de-4550-b9e0-2feda2c20e2b"},
    {"claim": "Brent traded near $73.", "subject": "Brent crude", "predicate": "traded near", "value": 73.0, "unit": "$/barrel", "period": "friday, june 26", "basis": "crude oil price", "source_sentence": "brent traded near $73.", "source_id": "68cf95a2-a7de-4550-b9e0-2feda2c20e2b"},
    {"claim": "Made up claim about unicorns worth $999.", "subject": "Unicorns", "predicate": "worth", "value": 999.0, "unit": "$", "period": "never", "basis": "fantasy", "source_sentence": "unicorns are worth $999.", "source_id": "fake"},
]

articles = [
    {"id": ["4a70ae7c"], "clean_text": ["west texas intermediate, the u.s. benchmark, settled below $70 a barrel on friday, june 26, for the first time since late february, according to cnbc. brent traded near $73. drivers feel it at the pump."]}
]

result = fact_check(claims, articles, threshold=0.25)
print(f"Verified {len(result)} of {len(claims)} claims")
for c in result:
    print(f"  - {c['claim']}")

assert len(result) == 2, f"Expected 2 verified claims, got {len(result)}"
assert result[0]["claim"] == "West Texas Intermediate settled below $70 a barrel."
assert result[1]["claim"] == "Brent traded near $73."
print("All tests passed!")
