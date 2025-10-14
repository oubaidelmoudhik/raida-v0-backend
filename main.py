import csv
import os
import json
import datetime
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
# from weasyprint import HTML
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

from preprocess_data import extract_title_info

load_dotenv()
# ---------------------------
# CONFIG
# ---------------------------
TEACHER_SUBJECT = os.getenv("TEACHER_SUBJECT", "French")
PARCOURS_COUNT = int(os.getenv("PARCOURS_COUNT"))

print(f"Using PARCOURS_COUNT={PARCOURS_COUNT}")

CSV_FILE = "cahier_journal_2parcours.csv" if PARCOURS_COUNT == 2 else "cahier_journal.csv"
PPTX_FILE = "Français_Niv5_Parcour1_Palier3_Séance1.pptx"

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs_mindmaps")
PPTX_DIR = "./lessons"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS_PARCOURS1 = [
    "Date",
    "titre",
    "Parcours",
    "Palier",
    "Séance",
    "Objectif",
    "Rituel",
    "Vocabulaire",
    "Lecture",
    "Écriture",
    "Pratique autonome",
    "Jeu",
    "Notes"
]
HEADERS_PARCOURS2 = [
    "Date", "titre1",
    "Palier1", "Séance1", "Objectif1", "Rituel1", "Vocabulaire1", "Lecture1", "Écriture1", "Pratique autonome1", "Jeu1", "Notes1","titre2",
    "Palier2", "Séance2", "Objectif2", "Rituel2", "Vocabulaire2", "Lecture2", "Écriture2", "Pratique autonome2", "Jeu2", "Notes2",
]
HEADERS = HEADERS_PARCOURS2 if PARCOURS_COUNT == 2 else HEADERS_PARCOURS1

sample_csv_row = {
    "Date": "2025-10-05",
    "Parcours": "Parcours 1",
    "Palier": "3",
    "Séance": "1",
    "Objectif": "Amener les élèves à lire et écrire des mots simples contenant les lettres m, n, s, l.",
    "Rituel": "Chanson d'accueil, dictée flash de lettres et correction collective.",
    "Vocabulaire": "Découverte des mots : maman, lune, sel, sol, melon, salle.",
    "Lecture": "Lecture de syllabes et de mots simples avec m, n, s, l.",
    "Écriture": "Écriture guidée de mots et phrases au tableau puis sur ardoise.",
    "Pratique autonome": "Exercices individuels page 10 et lecture à voix basse par binômes.",
    "Jeu": "Jeu du mot mystère : deviner le mot à partir d’indices sonores.",
    "Notes": "La moitié des élèves confondent n/m, besoin de rebrassage demain."
}

csv_data_2parcours = {
    "Date": "2025-10-10",
    # Parcours 1
    "Palier1": "1",
    "Séance1": "3",
    "Objectif1": "Lire et écrire des mots avec la lettre m.",
    "Rituel1": "Dictée de syllabes et mots simples : ma, mi, mu.",
    "Vocabulaire1": "maman, maison, main.",
    "Lecture1": "Texte court sur le mot 'maman'.",
    "Écriture1": "Copie des mots appris et une phrase simple.",
    "Pratique autonome1": "Jeux de lecture sur ardoise.",
    "Jeu1": "Cherche le mot dans le texte.",
    "Notes1": "Bon engagement du groupe 1.",
    # Parcours 2
    "Palier2": "2",
    "Séance2": "3",
    "Objectif2": "Lire et écrire des phrases simples contenant la lettre j.",
    "Rituel2": "Dictée de syllabes et mots : ja, je, jou.",
    "Vocabulaire2": "jupe, jardin, jaune.",
    "Lecture2": "Lecture d’un petit texte : 'Le jardin de Julie'.",
    "Écriture2": "Écriture de 2 phrases avec les mots du jour.",
    "Pratique autonome2": "Jeu de cartes syllabes à associer.",
    "Jeu2": "Mots cachés avec la lettre j.",
    "Notes2": "Bon progrès en lecture, attention à l’écriture."
}


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
    
def ensure_csv_exists():
    """Check if CSV exists, if not create it with headers."""
    print("Checking for CSV file...")
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            print("Creating CSV file...")
            writer = csv.writer(f)
            writer.writerow(HEADERS)


def entry_exists_in_csv(palier, seance):
    """Check if (Palier, Séance) already exist in local CSV."""
    if not os.path.exists(CSV_FILE):
        return False
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("Palier", "")).strip() == str(palier).strip() and str(row.get("Séance", "")).strip() == str(seance).strip():
                return True
    return False

def should_process(pptx_path: str) -> bool:
    """Return False if (Palier, Séance) already exist in CSV"""
    title, parcours, palier, seance = extract_title_info(pptx_path)

    # If missing numbers, skip automatically
    if not palier or not seance:
        print(f"⚠️ Skipping {pptx_path} — missing Palier or Séance info.")
        return False

    # Check CSV
    if entry_exists_in_csv(palier, seance):
        print(f"⏩ Skipping {pptx_path} — already in CSV (Palier {palier}, Séance {seance}).")
        return False

    return True

def process_with_ai(title, parcours, palier, seance, content):
    """Send PPTX content to AI and return structured JSON with CSV row + mindmap."""
    print("Processing with AI...")
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    # ---------------------------
    # AI PROMPT
    # ---------------------------
    prompt = f"""
You are a teaching assistant generating structured lesson data.

Return **only valid JSON**, no markdown, no extra text.

Follow **exactly** this structure and phrasing style, adapting the content to the slides provided::
{{
  "csv_row": {{
    "Date": "{today}",
    "titre": "{title}",
    "Parcours": "{parcours}",
    "Palier": "{palier}",
    "Séance": "{seance}",
    "Objectif": "Amener les élèves à comprendre, lire et produire des mots simples du vocabulaire et identifier/écrire les lettres a, i, b, d, e, é, o.",
    "Rituel": "Les élèves chantent « Bonjour les amis », réalisent une dictée flash de mots simples et corrigent collectivement sur ardoise.",
    "Vocabulaire": "Les élèves découvrent et répètent les mots de vocabulaire : ardoise, immeuble, olive, banane, dindon, melon, école, bébé.",
    "Lecture": "Les élèves lisent les lettres a, i, b, d, e, é, o en majuscules et minuscules, puis des mots simples (ananas, immeuble, banane, école).",
    "Écriture": "Les élèves écrivent sur ardoise et dans leur cahier les lettres et mots étudiés, après démonstration au tableau.",
    "Pratique autonome": "Les élèves complètent les activités du livret p.5 et p.7, relient lettres ↔ mots, lisent à voix basse en binômes et recopient les lettres.",
    "Jeu": "Les élèves participent à un jeu « Sauter sur les lettres » : ils sautent sur les cases contenant la lettre annoncée et lisent la syllabe.",
    "Notes": "quelques difficultes dans la séance..."
  }},
  "mindmap": "🧠 **Séance 5 – Palier 2**
🎯 **Objectif principal**
Lire, écrire et utiliser des syllabes et mots simples avec **p – q – qu – t – k – x** à travers du vocabulaire courant.
1. **Rituel**
* Dictée flash de mots connus (sous – sur – lavabo – chat)
* Écriture et correction sur ardoise
2. **Vocabulaire (images + répétition)**
   Mots : poule – coq – taxi – kiwi – savon – se laver – kilo – café
* Répétition chorale et individuelle
* Phrases simples :
  * La poule et le coq.
  * Le taxi est parti.
  * Le garçon se lave les mains avec du savon.
  * Un kilo de tomates.
  * Le café est chaud.
3. **Rebrassage du vocabulaire**
* Jeu « Numéro du mot » : écrire sur ardoise le numéro du mot entendu
* Jeu des images manquantes (taxi – se laver)
* Lecture rapide avec images au tableau
4. **Lecture – Écriture (lettres p, q, qu, t, k, x)**
* Lecture de syllabes : pa – pou – qu – ki – ta – tu – ke – xi…
* Lecture de mots : taxi – kimono – kilo – café – kimono – kiwi
* Lecture de phrases :
  * La dame a acheté un kilo de tomates.
  * Elle a mixé le kiwi.
  * La girafe est avec le petit.
  * Jamal adore le karaté.
* Écriture collective : « Le taxi est parti » (ardoise + cahier)
5. **Pratique autonome**
* Exercices du livret p.15 : activités 1 → 4
* Lecture à voix basse en binômes (échange des rôles)
* Copie de phrases et mots étudiés
6. **Jeu final**
* Jeu du panier des syllabes et lettres (p – q – qu – t – k – x)
* Panier qui circule avec cartes → un élève pioche → lit → la classe répète
7. **Devoir à la maison**
* Écrire les mots du vocabulaire (p.10)
* Relire activités 2 → 4 (p.15)
* Recopier activité 4 (p.15)
* Terminer activité 5 (p.15)
"
}}
Adapt this tone and sentence structure to the actual PPTX content provided below.
Write *original* sentences in the same pedagogical phrasing style — short, action-based, classroom-focused, and aligned with Moroccan French teaching style
Rules:
- Output must be strictly valid JSON that Python's json.loads() can parse.
- Never include ```json or other code fences.
- Escape internal quotes properly.
- Do not add explanations before or after the JSON.
- Base all content on the lesson slides below.

Lesson slides content:
{content}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role": "system", "content": "You generate structured JSON for a teacher's lesson journal."},
            {"role": "user", "content": prompt}
        ]
    )

    raw_result = response.choices[0].message.content.strip()

    # Try parsing JSON output
    try:
        raw_result = raw_result.replace("None", "null")
        data = json.loads(raw_result)
        csv_data = data["csv_row"]
        mindmap = data["mindmap"]
    except json.JSONDecodeError as e:
        print("❌ Invalid JSON received:", e)
        print("Raw output:\n", raw_result)
        return None, None

    return csv_data, mindmap


def append_to_csv(csv_data: dict):
    """Append a dict row (12 fields) to CSV safely."""
    ensure_csv_exists()
    print("Adding entry to CSV file...")
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, quoting=csv.QUOTE_ALL)
        writer.writerow(csv_data)

def save_mindmap(pptx_path: str, mindmap: str):
    """Save the mindmap as a Markdown file."""
    title, palier, seance = extract_title_info(pptx_path)
    print("Saving mind map...")
    today = datetime.date.today().strftime("%Y-%m-%d")
    filename = os.path.join(OUTPUT_DIR, f"{title}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(mindmap)
    return filename

# PROCCES 2 PARCOURS
def process_two_parcours(title1, parcours1, palier1, seance1, content1,
                         title2, parcours2, palier2, seance2, content2):
    # Process both parcours via AI
    csv_data1, mindmap1 = process_with_ai(title1, parcours1, palier1, seance1, content1)
    csv_data2, mindmap2 = process_with_ai(title2, parcours2, palier2, seance2, content2)

    # Validate outputs
    if not csv_data1 or not csv_data2:
        print("❌ Skipped one parcours due to invalid AI output.")
        return

    # Combine structured data
    combined = {
        "Date": csv_data1.get("Date", ""),
        # Parcours 1
        "titre1": csv_data1.get("titre", ""),
        "Palier1": csv_data1.get("Palier", ""),
        "Séance1": csv_data1.get("Séance", ""),
        "Objectif1": csv_data1.get("Objectif", ""),
        "Rituel1": csv_data1.get("Rituel", ""),
        "Vocabulaire1": csv_data1.get("Vocabulaire", ""),
        "Lecture1": csv_data1.get("Lecture", ""),
        "Écriture1": csv_data1.get("Écriture", ""),
        "Pratique autonome1": csv_data1.get("Pratique autonome", ""),
        "Jeu1": csv_data1.get("Jeu", ""),
        "Notes1": csv_data1.get("Notes", ""),
        # Parcours 2
        "titre2": csv_data1.get("titre", ""),
        "Palier2": csv_data2.get("Palier", ""),
        "Séance2": csv_data2.get("Séance", ""),
        "Objectif2": csv_data2.get("Objectif", ""),
        "Rituel2": csv_data2.get("Rituel", ""),
        "Vocabulaire2": csv_data2.get("Vocabulaire", ""),
        "Lecture2": csv_data2.get("Lecture", ""),
        "Écriture2": csv_data2.get("Écriture", ""),
        "Pratique autonome2": csv_data2.get("Pratique autonome", ""),
        "Jeu2": csv_data2.get("Jeu", ""),
        "Notes2": csv_data2.get("Notes", "")
    }

    # Save to CSV
    append_to_csv(combined)

    # Combine mindmaps into one Markdown file
    mindmap_combined = f"## Parcours 1 – {title1}\n{mindmap1}\n\n---\n\n## Parcours 2 – {title2}\n{mindmap2}"
    md_filename = f"{palier1}_P1S{seance1}_P2S{seance2}_2parcours.md"
    md_path = os.path.join(OUTPUT_DIR, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(mindmap_combined)

    # Generate PDF
    pdf_filename = f"{palier1}_P1S{seance1}_P2S{seance2}.pdf"
    generate_pdf_from_csv_data(combined, pdf_filename)
    print(f"✅ Combined PDF generated: {pdf_filename}")


def generate_pdf_from_csv_data(csv_row, pdf_filename):
    # 1️⃣ Render HTML with Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("template.html")
    html_content = template.render(csv_row=csv_row)

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
        browser = p.chromium.launch(headless=True)
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

def choose_lessons():
    """Let the user manually select two lessons (already loaded from JSON) to pair."""
    lessons = load_lessons_data()
    if not lessons:
        print("⚠️ No lessons available in data/lessons.json.")
        exit()

    print("\n📘 Available lessons:")
    for i, lesson in enumerate(lessons, start=1):
        print(f"  {i}. {lesson['title']} (Parcours {lesson['parcours']} - Palier {lesson['palier']} - Séance {lesson['seance']})")

    try:
        idx1 = int(input("\nEnter number for Parcours 1 lesson: ")) - 1
        idx2 = int(input("Enter number for Parcours 2 lesson: ")) - 1
    except ValueError:
        print("❌ Invalid input. Please enter valid numbers.")
        exit()

    if idx1 not in range(len(lessons)) or idx2 not in range(len(lessons)):
        print("❌ Invalid selection.")
        exit()

    lesson1 = lessons[idx1]
    lesson2 = lessons[idx2]

    print(f"\n✅ Selected:")
    print(f"  Parcours 1 → {lesson1['title']} (Palier {lesson1['palier']}, Séance {lesson1['seance']})")
    print(f"  Parcours 2 → {lesson2['title']} (Palier {lesson2['palier']}, Séance {lesson2['seance']})")

    return lesson1, lesson2


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    lessons = load_lessons_data()
    print(f"📘 Loaded {len(lessons)} lessons from JSON")

    if PARCOURS_COUNT == 1:
        for lesson in lessons:
            title = lesson["title"]
            parcours = lesson["parcours"]
            palier = lesson["palier"]
            seance = lesson["seance"]
            content = lesson["content"]

            # ✅ Skip if already processed (exists in CSV)
            if not should_process(f"{parcours}_Palier{palier}_Seance{seance}"):
                continue

            print("=" * 60)
            print(f"🚀 Processing: {title} (Palier {palier}, Séance {seance})")
            print("=" * 60)

            csv_data, mindmap = process_with_ai(title, parcours, palier, seance, content)

            if csv_data and mindmap:
                append_to_csv(csv_data)
                md_file = save_mindmap(f"{parcours}_Palier{palier}_Seance{seance}", mindmap)
                print(f"✅ Processed successfully → {md_file}")
                pdf_filename = f"Palier{palier}_Séance{seance}.pdf"
                generate_pdf_from_csv_data(csv_data, pdf_filename)
                print(f"📄 PDF created → {pdf_filename}")
            else:
                print(f"❌ Skipped {title} (invalid AI response)")

    else:
        # 🔁 Manual selection for 2 parcours (interactive)
        lesson1, lesson2 = choose_lessons()
        process_two_parcours(lesson1["title"], lesson1["parcours"], lesson1["palier"], lesson1["seance"], lesson1["content"],
                             lesson2["title"], lesson2["parcours"], lesson2["palier"], lesson2["seance"], lesson2["content"])
