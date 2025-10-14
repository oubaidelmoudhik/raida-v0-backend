import os
import json
from pptx import Presentation


LESSONS_DIR = "lessons"
OUTPUT_JSON = "data/lessons.json"

def extract_title_info(pptx_path: str):
    """Extract parcours, palier, and séance numbers from filename."""
    filename = os.path.basename(pptx_path)
    name, _ = os.path.splitext(filename)

    parcours, palier, seance = None, None, None
    parts = name.split("_")

    for part in parts:
        lower = part.lower()
        if lower.startswith("parcour"):
            parcours = part.replace("Parcour", "").replace("parcour", "")
        elif lower.startswith("palier"):
            palier = part.replace("Palier", "").replace("palier", "")
        elif lower.startswith("séance") or lower.startswith("seance"):
            seance = part.replace("Séance", "").replace("séance", "").replace("Seance", "").replace("seance", "")

    title = name.replace("_", " ")
    return title, parcours, palier, seance

def extract_text_from_pptx(file_path):
    prs = Presentation(file_path)
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def main():
    lessons = []
    for filename in os.listdir(LESSONS_DIR):
        if filename.endswith(".pptx"):
            path = os.path.join(LESSONS_DIR, filename)
            title, parcours, palier, seance = extract_title_info(path)
            content = extract_text_from_pptx(path)
            lessons.append({
                "id": len(lessons) + 1,
                "title": title,
                "parcours": parcours,
                "palier": palier,
                "seance": seance,
                "filename": filename,
                "content": content
            })

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
