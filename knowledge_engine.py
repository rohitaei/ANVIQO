import json

with open("knowledge.json", "r") as f:
    KNOWLEDGE = json.load(f)

def search_knowledge(question):
    q = question.lower()

    for topic, data in KNOWLEDGE.items():
        words = topic.lower().replace("-", " ").split()

        if any(word in q for word in words):
            return {
                "topic": topic,
                "checks": data.get("checks", []),
                "safety": data.get("safety", "")
            }

    return None
