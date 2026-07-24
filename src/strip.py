import re

# 3 functions from AI not fussed about learning how this works, the idea is that we want to
# provide two strings and remove the string from another but the template is gonna be in some
# weird MD format so has to have some extra preprocessing including some regular expressions
def _normalise(text):
    return re.sub(r'\s+', ' ', text).strip().lower()

def _strip_frontmatter(text: str) -> str:
    return re.sub(r'^---.*?---\s*,', '', text, flags=re.DOTALL)
    
def extract_user_content(body: str, template: str) -> str:
    template_clean = _strip_frontmatter(template)
        
    # split on markdown bold headers, keeping the headers
    sections = re.split(r'(\*\*[^*]+\*\*)', body)
    template_sections = re.split(r'(\*\*[^*]+\*\*)', template_clean)
        
    template_placeholders = {t.strip().lower() for t in template_sections if t.strip()}
        
    kept = []
    for part in sections:
        part_norm = part.strip().lower()
        if part_norm and part_norm not in template_placeholders:
            kept.append(part.strip())
        
    return "\n\n".join(kept)