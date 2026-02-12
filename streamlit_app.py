import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import json
import PyPDF2
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="VerveSchool CV Builder", layout="centered")

# API KEY LOGIC: Check Secrets first, then Sidebar
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Enter Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)

# *** THE FIX: SANITIZER FUNCTION ***
def sanitize_for_latin1(data):
    """Recursively traverses a dict/list and replaces non-latin-1 chars in strings."""
    if isinstance(data, dict):
        return {k: sanitize_for_latin1(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_latin1(elem) for elem in data]
    elif isinstance(data, str):
        # Replace common problematic characters
        return (data.replace('\u2013', '-')  # En dash
                    .replace('\u2014', '--') # Em dash
                    .replace('\u2018', "'")  # Left single quote
                    .replace('\u2019', "'")  # Right single quote
                    .replace('\u201c', '"')  # Left double quote
                    .replace('\u201d', '"')) # Right double quote
    else:
        return data

# --- 2. THE MASTER TABLE PDF ENGINE (LOCKED BLUEPRINT) ---
class VerveTablePDF(FPDF):
    def section_header(self, title):
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(82, 101, 109) # Dark Slate Gray
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, title, 1, 1, 'C', 1)
        self.set_text_color(0, 0, 0)

    def role_header(self, title):
        self.set_font('Arial', 'B', 11)
        self.set_fill_color(225, 222, 214) # Beige/Light Gray
        self.set_text_color(0, 0, 0)
        self.cell(0, 6, title, 1, 1, 'C', 1)

def generate_pdf(data):
    pdf = VerveTablePDF()
    
    side_margin = 12.7 
    top_margin = 28  
    pdf.set_margins(side_margin, top_margin, side_margin)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    effective_content_width = pdf.w - (2 * side_margin)

    # --- NAME & CONTACT ---
    pdf.set_font('Arial', 'B', 21)
    pdf.cell(0, 8, data.get('name', 'NAME – BDA').upper(), 0, 1, 'C')
    pdf.ln(1)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 6, f"{data.get('email', '')} | {data.get('phone', '')} | {data.get('location', '')}", 0, 1, 'C')
    pdf.ln(3)

    # --- ACADEMIC QUALIFICATIONS ---
    pdf.section_header('ACADEMIC QUALIFICATIONS')
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(225, 222, 214)
    
    w_qual = effective_content_width * 0.4
    w_inst = effective_content_width * 0.4
    w_year = effective_content_width * 0.2
    
    pdf.cell(w_qual, 7, '  Qualification', 1, 0, 'L', 1)
    pdf.cell(w_inst, 7, '  Institute', 1, 0, 'L', 1)
    pdf.cell(w_year, 7, '  Year', 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 10)
    academic_height = 12
    
    for edu in data.get('education', []):
        pdf.set_font('Arial', '', 10)
        pdf.cell(w_qual, academic_height, f"  {edu.get('degree', '')}", 1)
        pdf.cell(w_inst, academic_height, f"  {edu.get('institute', '')}", 1)
        pdf.cell(w_year, academic_height, f"{edu.get('year', '')}", 1, 1, 'C')

    # --- PROFESSIONAL EXPERIENCE ---
    pdf.section_header('PROFESSIONAL EXPERIENCE')
    
    bullet_indent_x = pdf.l_margin + 3
    bullet_char_width = 4
    bullet_text_width = effective_content_width - 6
    line_h = 6
    inner_pad = 6
    rect_x = pdf.l_margin
    rect_width = effective_content_width

    # Role 1: VerveSchool
    pdf.role_header('Sales Fellow | VerveSchool Talent Fund | 2026')
    start_y = pdf.get_y()
    pdf.ln(inner_pad)
    pdf.set_x(bullet_indent_x)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(bullet_text_width, line_h, 'VerveSchool helps growth stage startups hire and develop early career sales talent.')
    
    verve_bullets = [
        "Undergoing training in buyer psychology, lead qualification, and high volume pipeline building.",
        "Prepared for on the job sales coaching and founder mentorship."
    ]
    for b in verve_bullets:
        pdf.set_font('Arial', '', 10)
        pdf.set_x(bullet_indent_x)
        pdf.cell(bullet_char_width, line_h, chr(149), 0, 0)
        pdf.multi_cell(bullet_text_width, line_h, b)
    
    pdf.ln(inner_pad)
    pdf.rect(rect_x, start_y, rect_width, pdf.get_y() - start_y)

    # Dynamic Roles
    for role in data.get('experience', []):
        if pdf.get_y() > 240: pdf.add_page()
            
        header_text = f"{role.get('role', '')} | {role.get('company', '')} | {role.get('dates', '')}"
        pdf.role_header(header_text)
        start_y = pdf.get_y()
        pdf.ln(inner_pad)
        
        for b in role.get('bullets', []):
            pdf.set_font('Arial', '', 10)
            pdf.set_x(bullet_indent_x)
            pdf.cell(bullet_char_width, line_h, chr(149), 0, 0)
            pdf.multi_cell(bullet_text_width, line_h, b)
            
        pdf.ln(inner_pad)
        pdf.rect(rect_x, start_y, rect_width, pdf.get_y() - start_y)

    # --- NOTABLE ACTIVITIES ---
    if pdf.get_y() > 240: pdf.add_page()
    pdf.section_header('NOTABLE ACTIVITIES & SKILLS')
    
    start_y = pdf.get_y()
    pdf.ln(inner_pad)
    for b in data.get('activities', []):
        pdf.set_font('Arial', '', 10)
        pdf.set_x(bullet_indent_x)
        pdf.cell(bullet_char_width, line_h, chr(149), 0, 0)
        pdf.multi_cell(bullet_text_width, line_h, b)
    
    pdf.ln(inner_pad)
    pdf.rect(rect_x, start_y, rect_width, pdf.get_y() - start_y)

    # Return bytes, NOT a latin-1 encoded string
    return pdf.output(dest='S').encode('latin-1')

# --- 3. AI EXTRACTION LOGIC ---
def extract_data_from_cv(text):
    prompt = """
    You are an expert Resume Architect. Extract data from this resume text and format it into JSON.
    RULES:
    1. Name: Format as "FULL NAME – BDA".
    2. Professional Experience: Rewrite bullets to be "Alex Hormozi style" (Action + Metric + Result). Keep it dense. 
    3. Exclude 'VerveSchool' from the experience list (it is added automatically).
    4. Education: Only Degree, Institute, and Year.
    5. Activities: Combine Skills, Certifications, and Hobbies into a single list of high-impact bullets.
    JSON STRUCTURE:
    {
        "name": "NAME – BDA",
        "email": "email",
        "phone": "phone",
        "location": "City",
        "education": [
            {"degree": "Degree Name", "institute": "Institute Name", "year": "Year"}
        ],
        "experience": [
            {
                "role": "Role Name",
                "company": "Company Name",
                "dates": "Month Year - Month Year",
                "bullets": ["Bullet 1", "Bullet 2", "Bullet 3"]
            }
        ],
        "activities": ["Activity 1", "Activity 2", "Skill 1", "Certification 1"]
    }
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    response = model.generate_content(prompt + "\n\nRESUME TEXT:\n" + text)
    json_str = response.text.replace('```json', '').replace('```', '')
    return json.loads(json_str)

# --- 4. THE UI ---
st.title("VerveSchool CV Builder 🚀")
st.write("Upload a draft PDF. Get the **Master Table** Format instantly.")

uploaded_file = st.fi
