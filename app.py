from flask import Flask, request, jsonify, send_file
import os
from flask_cors import CORS
import json

# Import from main and preprocess_data
from pdf_generator import generate_pdf_from_lesson_data, process_with_ai, generate_mindmap_from_lesson_data
# Trigger reload, process_with_ai
from preprocess_data import extract_metadata_from_filename, extract_text_from_pptx, update_lessons_registry
from cache import lesson_cache

app = Flask(__name__)

# Configure CORS to allow Vercel frontend
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # Local development
            "https://*.vercel.app",   # Vercel preview deployments
            "https://your-domain.com" # Your production domain (update this)
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

@app.route("/")
def home():
    return {"status": "running", "service": "raida-backend"}

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
    
    # Generate Mind Map
    mindmap_filename = f"MindMap_Period{meta['period']}_Week{meta['week']}_Session{meta['session']}.pdf"
    mindmap_path = generate_mindmap_from_lesson_data(lesson_data, mindmap_filename)
    
    return jsonify({
        "title": meta["title"],
        "lesson_data": lesson_data,
        "pdf_path": pdf_path,
        "mindmap_pdf_path": mindmap_path
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

    mindmap_filename = f"MindMap_{lesson['title']}.pdf"
    mindmap_path = generate_mindmap_from_lesson_data(lesson_data, mindmap_filename)

    return jsonify({
        "title": lesson["title"],
        "lesson_data": lesson_data,
        "pdf_path": pdf_path,
        "mindmap_pdf_path": mindmap_path
    })

import threading
import time

def delete_file_later(file_path, delay=120):
    """Delete a file after a specified delay in seconds."""
    def delayed_delete():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting file {file_path}: {e}")
            
    thread = threading.Thread(target=delayed_delete)
    thread.daemon = True
    thread.start()

@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    """Serve a generated PDF for download and schedule its deletion."""
    pdf_path = os.path.join("output_pdfs", filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not found"}), 404
        
    # Schedule deletion after 2 minutes (120 seconds)
    delete_file_later(pdf_path, delay=120)
    
    return send_file(pdf_path, as_attachment=True)

@app.route("/lessons", methods=["GET"])
def get_lessons():
    # Scan for new files first
    update_lessons_registry()
    
    with open("data/lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)
    # Return full lesson objects
    return jsonify(lessons)
    


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics."""
    stats = lesson_cache.get_stats()
    return jsonify(stats)

@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    """Clear all cache entries."""
    lesson_cache.clear()
    return jsonify({"message": "Cache cleared successfully"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
