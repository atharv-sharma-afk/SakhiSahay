import sys
from pathlib import Path
import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from app.rag.retriever import retrieve
from app.rag.language import detect_language

with open("evaluation/eval_questions.yaml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

print(f"{'ID':<10} | {'CAT':<14} | {'BEST':<6} | {'CHUNKS':<6} | QUESTION")
print("-" * 75)
for q in data["questions"]:
    lang = detect_language(q["question"])
    res = retrieve(q["question"], language=lang)
    best_str = f"{res.best_score:.3f}" if res.best_score is not None else "None"
    print(f"{q['id']:<10} | {q['category']:<14} | {best_str:<6} | {len(res.chunks):<6} | {q['question'][:45]}")
