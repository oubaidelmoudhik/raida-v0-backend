import os
import json
import re
from pptx import Presentation

LESSONS_DIR = "lessons"
OUTPUT_JSON = "data/lessons.json"

def extract_metadata_from_filename(filename: str):
    """
    Extract metadata from filename.
    Supports formats:
    1. FR_N5_P1_SEM1_S3_V2.pptx (Short code)
    2. Français_Niv5_Parcour1_Palier3_Séance1.pptx (Long format)
    """
    name, _ = os.path.splitext(filename)
    parts = name.split("_")
    
    metadata = {
        "title": name.replace("_", " "),
        "subject": "français", # Default
        "level": "5",
        "period": "",
        "week": "",
        "session": ""
    }

    # Try Short Format: FR_N5_P1_SEM1_S3...
    if len(parts) >= 5 and len(parts[0]) <= 4:
        # Subject
        if parts[0].upper() == "FR": metadata["subject"] = "français"
        elif parts[0].upper() == "MATH": metadata["subject"] = "mathématiques"
        
        # Level
        if parts[1].startswith("N"): metadata["level"] = parts[1][1:]
        
        # Period (P)
        if parts[2].startswith("P"): metadata["period"] = parts[2][1:]
        
        # Semaine (SEM) -> Week
        if parts[3].startswith("SEM"): metadata["week"] = parts[3][3:]
        
        # Seance (S) -> Session
        if parts[4].startswith("S"): metadata["session"] = parts[4][1:]

    # Try Long Format: Français_Niv5_Parcour1_Palier3_Séance1
    else:
        for part in parts:
            lower = part.lower()
            if "français" in lower: metadata["subject"] = "français"
            elif "math" in lower: metadata["subject"] = "mathématiques"
            
            if lower.startswith("niv"): metadata["level"] = lower.replace("niv", "")
            
            if lower.startswith("parcour"):
                # Map Parcour to Week? Or Period?
                # User example: Parcour1 -> Week 2? 
                # For now, let's map Parcour -> Week as it's the closest equivalent in hierarchy
                metadata["week"] = part.lower().replace("parcour", "").replace("s", "")
            
            if lower.startswith("palier"):
                metadata["period"] = part.lower().replace("palier", "")
                
            if lower.startswith("séance") or lower.startswith("seance"):
                metadata["session"] = part.lower().replace("séance", "").replace("seance", "")

    return metadata

def extract_text_from_pptx(file_path):
    try:
        prs = Presentation(file_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def extract_objective(content: str):
    """Try to extract objective from content."""
    lines = content.split('\n')
    for line in lines:
        if "objectif" in line.lower() or "capable de" in line.lower():
            # Clean up the line
            return line.strip()
    return "......"

def main():
    lessons = []
    
    # Ensure lessons dir exists
    if not os.path.exists(LESSONS_DIR):
        print(f"Directory {LESSONS_DIR} not found.")
        return

    files = sorted([f for f in os.listdir(LESSONS_DIR) if f.endswith(".pptx")])
    
    for filename in files:
        path = os.path.join(LESSONS_DIR, filename)
        print(f"Processing {filename}...")
        
        content = extract_text_from_pptx(path)
        meta = extract_metadata_from_filename(filename)
        objective = extract_objective(content)
        
        lessons.append({
            "id": len(lessons) + 1,
            "title": meta["title"],
            "subject": meta["subject"],
            "level": meta["level"],
            "period": meta["period"],
            "week": meta["week"],
            "session": meta["session"],
            "filename": filename,
            "objective": objective,
            "content": content
        })

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)
    
    print(f"Processed {len(lessons)} lessons to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
