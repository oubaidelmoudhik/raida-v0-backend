from flask import Flask, request, jsonify, send_file
import os
from flask_cors import CORS
import json

from main import append_to_csv, extract_title_info, ensure_csv_exists, entry_exists_in_csv, generate_pdf_from_csv_data, process_with_ai

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
    title, palier, seance = extract_title_info(pptx_path)
    ensure_csv_exists()
    csv_data, mindmap = process_with_ai(pptx_path)
    if not csv_data:
        return jsonify({"error": "AI analysis failed"}), 500

    csv_data["Palier"] = palier
    csv_data["Séance"] = seance
    append_to_csv(csv_data)

    # Generate PDF
    pdf_filename = f"Palier{palier}_Seance{seance}.pdf"
    pdf_path = generate_pdf_from_csv_data(csv_data, pdf_filename)
    result = jsonify({
        "title": title,
        "csv_data": csv_data,
        "mindmap": mindmap,
        "pdf_path": pdf_path
    })
    print("Result:", result)
    return result

@app.route("/generate_from_id/<int:lesson_id>", methods=["POST"])
def generate_from_id(lesson_id):
    with open("data/lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404

    csv_data, mindmap = process_with_ai(lesson["title"], lesson["parcours"], lesson["palier"], lesson["seance"], lesson["content"])  

    pdf_filename = f"{lesson['title']}.pdf"
    pdf_path = generate_pdf_from_csv_data(csv_data, pdf_filename)

    return jsonify({
        "title": lesson["title"],
        "csv_data": csv_data,
        "mindmap": mindmap,
        "pdf_path": pdf_path
    })

@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    """Serve a generated PDF for download."""
    pdf_path = os.path.join("output_pdfs", filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not found"}), 404
    return send_file(pdf_path, as_attachment=True)

@app.route("/lessons", methods=["GET"])
def get_lessons():
    with open("data/lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)
    # Return just titles and IDs for selection
    return jsonify([{"id": l["id"], "title": l["title"]} for l in lessons])

if __name__ == "__main__":
    app.run(debug=True, port=5000)










