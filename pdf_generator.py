import os
import json
import datetime
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from preprocess_data import extract_metadata_from_filename
from cache import lesson_cache

load_dotenv()

# ---------------------------
# CONFIG
# ---------------------------
TEACHER_SUBJECT = os.getenv("TEACHER_SUBJECT", "French")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs_pdfs") # Changed default to reflect PDFs
PPTX_DIR = "./lessons"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------
# HELPERS
# ---------------------------
def load_lessons_data(json_path="data/lessons.json"):
    """Load all lessons data extracted by extract_lessons.py"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} not found. Run extract_lessons.py first.")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Define specific lesson steps
LESSON_STEPS = {
    "français": {
        "1": ["Présentation du vocabulaire", "Exploitation du vocabulaire", "Activités de vocabulaire sur livret"],
        "2": ["Oral – Acte de parole 1", "Ecrit – Point de langue 1", "Lecture – Mots avec difficultés"],
        "3": ["Oral - Acte de parole 2", "Ecrit – Point de langue 2", "Lecture – Phrases"],
        "4": ["Oral – Dialogue", "Lecture – Texte ( fluidité et compréhension)"],
        "5": ["Oral – Prise de parole", "Ecriture – Texte"],
        "6": ["Révision", "Lecture offerte"]
    },
    "mathématiques": {
        "default": ["الافتتاح", "النمذجة","الممارسة الموجهة", "الممارسة المستقلة", "اختتام الحصة"],
        "5": ["افتتاح الدرس", "مراجعة الدرس 1", "مراجعة الدرس 2", "مراجعة الدرس 3", "مراجعة الدرس 4", "اختتام الحصة"]
    },
    "langue arabe": {
        "default": ["الافتتاح", "النمذجة","الممارسة الموجهة" "الممارسة المستقلة", "اختتام الحصة"]
    }
}

def get_lesson_steps(subject, session):
    """Get specific lesson steps based on subject and session."""
    subj_lower = subject.lower()
    sess_str = str(session)
    
    if "français" in subj_lower:
        return LESSON_STEPS["français"].get(sess_str, [])
    
    elif "math" in subj_lower:
        print(f"DEBUG: Math session check. Session: '{sess_str}'")
        try:
            if sess_str == "5":
                return LESSON_STEPS["mathématiques"]["5"]
            elif sess_str == "6":
                return LESSON_STEPS["mathématiques"].get("5", LESSON_STEPS["mathématiques"]["default"])
            return LESSON_STEPS["mathématiques"]["default"]
        except KeyError as e:
            print(f"ERROR: KeyError accessing LESSON_STEPS for math session {sess_str}: {e}")
            return LESSON_STEPS["mathématiques"]["default"]
        
    elif "arabe" in subj_lower:
        return LESSON_STEPS["langue arabe"]["default"]
        
    return []

def process_with_ai(title, subject, level, period, week, session, content):
    """Send PPTX content to AI and return structured JSON with lesson data."""
    print(f"Processing with AI... Subject: {subject}, Session: {session}")
    
    # Determine language and prompt based on subject
    subj_lower = subject.lower()
    is_math = "math" in subj_lower
    is_arabe = "arabe" in subj_lower
    language = "Arabic" if (is_math or is_arabe) else "French"
    
    # 🔍 Check cache first
    cached_data = lesson_cache.get(content, language, subject, str(session))
    if cached_data:
        print(f"⚡ Returning cached lesson data (saved API call!)")
        return cached_data
    
    # Get specific steps
    specific_steps = get_lesson_steps(subject, session)
    steps_instruction = ""
    if specific_steps:
        steps_list = "\n".join([f"- {step}" for step in specific_steps])
        steps_instruction = f"""
IMPORTANT: You MUST use EXACTLY these lesson steps in this order:
{steps_list}

For each step, extract relevant content from the slides and assign a realistic duration.
"""
    
    # ---------------------------
    # SUBJECT-SPECIFIC AI PROMPTS
    # ---------------------------
    
    if language == "Arabic":
        # Arabic prompt (Math or Arabic)
        prompt = f"""
You are a teaching assistant generating structured lesson data for a lesson in Arabic.

Return **only valid JSON**, no markdown, no extra text.

{steps_instruction}

Analyze the lesson content and fill in the content for each step. Each step should have:
- name (EXACTLY as specified above)
- duration as in the content (e.g., "10min", "20min")
- icon (emoji)
- content (description in Arabic based on slides)

**OBJECTIVE EXTRACTION (CRITICAL):**
- Extract the main pedagogical objective from the lesson content.
- The objective should be specific, measurable, and action-oriented.
- Example: "تعلم قراءة وكتابة الأعداد من الملايين بالأرقام والحروف"
- Example: "حل مسائل متعلقة بوضعية البحث عن الكل أو الجزء"
- If no explicit objective is found, infer it from the lesson title and content.
- Do NOT use placeholders like "هدف الدرس" or "......".

**PHRASING STYLE (CRITICAL):**
- Use **pedagogical phrasing** describing what the students do.
- Start sentences with **"يقوم التلاميذ بـ..."** or **"يبدأ التلاميذ..."** or **"يشارك التلاميذ..."**.
- Example: "يبدأ التلاميذ بحساب ذهني سريع، ويكتبون النتائج على ألواحهم ثم يصححون بشكل جماعي."
- Example: "يقرأ التلاميذ النص ويستخرجون الكلمات الصعبة."
- Avoid passive voice or simple copying of slide text.

**SPECIFIC CONTENT RULES (CRITICAL):**
- For the step **"الافتتاح"** (Opening): The content MUST explicitly mention correcting homework and mental arithmetic (تصحيح الواجبات المنزلية والحساب الذهني), adapting the specific details to the lesson's context.
- For the step **"النمذجة"** (Modeling): Students do NOT participate in this step. The description must state that they are attentive/listening to the teacher's explanation (ينتبهون للشرح) without active participation.

Follow **exactly** this structure:
{{
  "lesson_data": {{
    "subject": "{subject}",
    "level": "{level}",
    "period": "{period}",
    "week": "{week}",
    "session": "{session}",
    "objective": "هدف الدرس بالعربية",
    "steps": [
      {{
        "name": "Step Name",
        "duration": "10min",
        "icon": "📝",
        "content": "يبدأ التلاميذ بحساب ذهني..."
      }}
      // ... other steps
    ]
  }}
}}

Rules:
- All text must be in Arabic
- Use ONLY the specified lesson steps
- Include realistic durations based on the content
- Output must be strictly valid JSON that Python's json.loads() can parse
- Never include ```json or other code fences
- Escape internal quotes properly
- Do not add explanations before or after the JSON

Lesson slides content:
{content}
"""
    else:
        # French prompt
        prompt = f"""
You are a teaching assistant generating structured lesson data for a French lesson.

Return **only valid JSON**, no markdown, no extra text.

{steps_instruction}

Analyze the lesson content and fill in the content for each step. Each step should have:
- name (EXACTLY as specified above)
- duration (e.g., "10min", "20min")
- icon (emoji)
- content (description in French based on slides)

**OBJECTIVE EXTRACTION (CRITICAL):**
- Extract the main pedagogical objective from the lesson content.
- The objective should be specific, measurable, and action-oriented.
- Example: "Utiliser les indicateurs de lieu et leurs contraires"
- Example: "Lire et comprendre des phrases sur les déplacements"
- If no explicit objective is found, infer it from the lesson title and content.
- Do NOT use placeholders like "Objectif de la leçon" or "......".

**PHRASING STYLE (CRITICAL):**
- Use **pedagogical phrasing** describing what the students do.
- Start sentences with **"Les élèves [action]..."**.
- Example: "Les élèves lisent un texte sur les déplacements et identifient les phrases clés."
- Example: "Les élèves commencent par un calcul mental, écrivent les résultats et corrigent ensemble."
- Example: "Les élèves rédigent un paragraphe en utilisant des mots donnés."
- Avoid passive voice or simple copying of slide text.

Follow **exactly** this structure:
{{
  "lesson_data": {{
    "subject": "{subject}",
    "level": "{level}",
    "period": "{period}",
    "week": "{week}",
    "session": "{session}",
    "objective": "Objectif de la leçon en français",
    "steps": [
      {{
        "name": "Step Name",
        "duration": "10min",
        "icon": "📝",
        "content": "Les élèves observent l'image..."
      }}
      // ... other steps
    ]
  }}
}}

Rules:
- All text must be in French
- Use ONLY the specified lesson steps
- Include realistic durations based on the content
- Output must be strictly valid JSON that Python's json.loads() can parse
- Never include ```json or other code fences
- Escape internal quotes properly
- Do not add explanations before or after the JSON
- Use Moroccan French teaching style (action-based, classroom-focused)

Lesson slides content:
{content}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": f"You generate structured JSON for a teacher's lesson journal in {language}."},
            {"role": "user", "content": prompt}
        ]
    )

    raw_result = response.choices[0].message.content.strip()


    # Try parsing JSON output
    try:
        raw_result = raw_result.replace("None", "null")
        data = json.loads(raw_result)
        lesson_data = data["lesson_data"]
        
        # Validate required fields
        if not lesson_data.get("objective") or lesson_data["objective"] in ["......", "Objectif de la leçon", "هدف الدرس"]:
            print("⚠️  Warning: Objective is missing or placeholder. Using fallback.")
            lesson_data["objective"] = f"Lesson on {subject} - Session {session}"
        
        if not lesson_data.get("steps") or not isinstance(lesson_data["steps"], list):
            print("❌ Error: Steps are missing or invalid")
            return None
        
        if len(lesson_data["steps"]) == 0:
            print("❌ Error: No steps extracted")
            return None
        
        print(f"✅ Successfully extracted {len(lesson_data.get('steps', []))} lesson steps")
        
        # 💾 Store in cache for future use
        lesson_cache.set(content, language, subject, str(session), lesson_data)
        
    except json.JSONDecodeError as e:
        print("❌ Invalid JSON received:", e)
        print("Raw output:\n", raw_result)
        return None
    except KeyError as e:
        print(f"❌ Missing required field: {e}")
        return None

    # Inject title and subject into lesson_data
    lesson_data["title"] = title
    lesson_data["subject"] = subject
    
    return lesson_data


def get_teacher_info(language="fr", subject_name=""):
    """Load teacher info from JSON based on language, removing blank optional fields."""
    teacher_info_path = os.path.join(os.path.dirname(__file__), ".", "teacherInfo.json")
    final_info = {}
    
    if os.path.exists(teacher_info_path):
        try:
            with open(teacher_info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
                if isinstance(info, list) and len(info) > 0:
                    raw_data = info[0].get(language, {})
                    
                    # exclude 'Matière'/'المادة' from file to strictly use document info
                    keys_to_exclude = ["Matière", "المادة"]
                    
                    for k, v in raw_data.items():
                        if k not in keys_to_exclude and v and str(v).strip():
                            final_info[k] = v
        except Exception as e:
            print(f"❌ Error loading teacher info: {e}")
            
    # Auto-inject Subject if not manually set (though user requested manual setting from document)
    if language == "ar":
        final_info["المادة"] = subject_name if subject_name else "الرياضيات" # Default fallback
    else:
        final_info["Matière"] = subject_name if subject_name else "Français"
        
    return final_info

def generate_pdf_from_lesson_data(lesson_data, pdf_filename):
    # Select template based on subject
    subject = lesson_data.get("subject", "français").lower()
    
    # Determine template and language
    if "math" in subject or "رياضيات" in subject:
        template_name = "template_math.html"
        lang_key = "ar"
        print("📐 Using Math template (Arabic)")
    elif "arabe" in subject or "عربية" in subject:
        template_name = "template_arabe.html"
        lang_key = "ar"
        print("🌙 Using Arabic template")
    else:
        template_name = "template_french.html"
        lang_key = "fr"
        print("📚 Using French template")
    
    # Load teacher info
    # Pass the detected subject name for display
    display_subject = "الرياضيات" if ("math" in subject or "رياضيات" in subject) else \
                      "اللغة العربية" if ("arabe" in subject or "عربية" in subject) else \
                      "Français"
                      
    teacher_data = get_teacher_info(lang_key, display_subject)

    # 1️⃣ Render HTML with Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template(template_name)
    html_content = template.render(lesson_data=lesson_data, teacher_data=teacher_data)

    # 2️⃣ Save temporary HTML file
    os.makedirs("temp_html", exist_ok=True)
    html_path = os.path.join("temp_html", "temp.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3️⃣ Define PDF output path
    os.makedirs("output_pdfs", exist_ok=True)
    pdf_path = os.path.join("output_pdfs", pdf_filename)

    # 4️⃣ Render and export with Playwright (headless Chromium)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--lang=ar"])
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(html_path)}")
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
        )
        browser.close()

    print(f"✅ PDF created: {pdf_path}")
    return pdf_path





# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    lessons = load_lessons_data()
    print(f"📘 Loaded {len(lessons)} lessons from JSON")

    for lesson in lessons:
        title = lesson["title"]
        parcours = lesson["parcours"]
        palier = lesson["palier"]
        seance = lesson["seance"]
        content = lesson["content"]

        print("=" * 60)
        print(f"🚀 Processing: {title} (Palier {palier}, Séance {seance})")
        print("=" * 60)

        lesson_data = process_with_ai(title, parcours, palier, seance, content)

        if lesson_data:
            pdf_filename = f"Palier{palier}_Séance{seance}.pdf"
            generate_pdf_from_lesson_data(lesson_data, pdf_filename)
            print(f"📄 PDF created → {pdf_filename}")
        else:
            print(f"❌ Skipped {title} (invalid AI response)")
