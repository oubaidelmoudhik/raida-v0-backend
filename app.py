from flask import Flask, request, jsonify, send_file
import os
from flask_cors import CORS


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
    # if entry_exists_in_csv(palier, seance):
    #     return jsonify({"error": f"Lesson Palier {palier} Séance {seance} already processed."}), 409
    # AI processing
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

@app.route("/download_pdf/<filename>")
def download_pdf(filename):
    """Serve a generated PDF for download."""
    pdf_path = os.path.join("output_pdfs", filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not found"}), 404
    return send_file(pdf_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)










