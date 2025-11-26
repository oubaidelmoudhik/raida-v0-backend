from flask import Flask, request, jsonify, send_file
import os
from flask_cors import CORS
import json

# Import from main and preprocess_data
from main import generate_pdf_from_lesson_data, process_with_ai
# Trigger reload, process_with_ai
from preprocess_data import extract_metadata_from_filename, extract_text_from_pptx

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"error": "No file provided"}), 400

    lessons_dir = "lessons"
    os.makedirs(lessons_dir, exist_ok=True)
    pptx_path = os.path.join(lessons_dir, uploaded_file.filename)
    uploaded_file.save(pptx_path)

    # Extract metadata
    meta = extract_metadata_from_filename(uploaded_file.filename)
    
    # Extract content
    content = extract_text_from_pptx(pptx_path)

    # Process with AI
    lesson_data = process_with_ai(meta["title"], meta["subject"], meta["level"], meta["period"], meta["week"], meta["session"], content)
    
    if not lesson_data:
        return jsonify({"error": "AI analysis failed"}), 500

    # Generate PDF
    pdf_filename = f"Period{meta['period']}_Week{meta['week']}_Session{meta['session']}.pdf"
    pdf_path = generate_pdf_from_lesson_data(lesson_data, pdf_filename)
    
    return jsonify({
        "title": meta["title"],
        "lesson_data": lesson_data,
        "pdf_path": pdf_path
    })

@app.route("/generate_from_id/<int:lesson_id>", methods=["POST"])
def generate_from_id(lesson_id):
    with open("data/lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404

    # Here we have all the info
    lesson_data = process_with_ai(lesson["title"], lesson["subject"], lesson["level"], lesson["period"], lesson["week"], lesson["session"], lesson["content"])  
    
    if not lesson_data:
        return jsonify({"error": "AI analysis failed"}), 500

    pdf_filename = f"{lesson['title']}.pdf"
    pdf_path = generate_pdf_from_lesson_data(lesson_data, pdf_filename)

    return jsonify({
        "title": lesson["title"],
        "lesson_data": lesson_data,
        "pdf_path": pdf_path
    })

@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    """Serve a generated PDF for download."""
    pdf_path = os.path.join("output_pdfs", filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not found"}), 404
    return send_file(pdf_path, as_attachment=True)

def scan_lessons_directory():
    """Scan lessons directory for new PPTX files and add them to lessons.json."""
    lessons_dir = "lessons"
    json_path = "data/lessons.json"
    
    if not os.path.exists(lessons_dir):
        os.makedirs(lessons_dir)
        return

    # Load existing lessons
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                lessons = json.load(f)
            except json.JSONDecodeError:
                lessons = []
    else:
        lessons = []

    # Get existing filenames
    existing_filenames = {l.get("filename") for l in lessons}
    
    # Scan directory
    files = [f for f in os.listdir(lessons_dir) if f.endswith(".pptx")]
    new_files_found = False

    for filename in files:
        if filename not in existing_filenames:
            print(f"🔍 New lesson found: {filename}")
            pptx_path = os.path.join(lessons_dir, filename)
            
            # Extract metadata and content
            try:
                meta = extract_metadata_from_filename(filename)
                content = extract_text_from_pptx(pptx_path)
                
                # Generate new ID
                new_id = max([l["id"] for l in lessons], default=0) + 1
                
                new_lesson = {
                    "id": new_id,
                    "title": meta["title"],
                    "subject": meta["subject"],
                    "level": meta["level"],
                    "period": meta["period"],
                    "week": meta["week"],
                    "session": meta["session"],
                    "filename": filename,
                    "objective": "......", # Placeholder
                    "content": content
                }
                
                lessons.append(new_lesson)
                new_files_found = True
                print(f"✅ Added lesson: {filename}")
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")

    # Save if changes made
    if new_files_found:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(lessons, f, ensure_ascii=False, indent=2)
            print("💾 lessons.json updated")

@app.route("/lessons", methods=["GET"])
def get_lessons():
    # Scan for new files first
    scan_lessons_directory()
    
    with open("data/lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)
    # Return full lesson objects
    return jsonify(lessons)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
