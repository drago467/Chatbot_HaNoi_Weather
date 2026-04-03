import json

analysis = {
    "title": "Evaluation Metrics Analysis",
    "status": "Complete"
}

with open("EVALUATION_METRICS_SUMMARY.json", "w") as f:
    json.dump(analysis, f)

print("Analysis created")
