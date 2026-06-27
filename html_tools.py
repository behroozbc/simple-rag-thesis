from bs4 import BeautifulSoup
def clean_html(html_string: str) -> str:
    soup = BeautifulSoup(html_string, 'lxml')  # or 'html.parser'
    
    # Remove all <style> and <script> tags
    for tag in soup.find_all(['style', 'script']):
        tag.decompose()
    
    # Remove all style attributes
    for tag in soup.find_all(True):  # all tags
        if tag.has_attr('style'):
            del tag['style']
    
    # Remove all class attributes
    for tag in soup.find_all(True):
        if tag.has_attr('class'):
            del tag['class']
    
    # Optional: Remove other common heavy attributes
    attributes_to_remove = ['id', 'onclick', 'onload', 'onmouseover', 
                          'data-', 'aria-', 'role']
    
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if any(attr.startswith(prefix) for prefix in ['data-', 'aria-']) or \
               attr in attributes_to_remove:
                del tag[attr]
    
    # Optional: Remove empty tags (except <br>, <img>, etc.)
    for tag in soup.find_all(True):
        if not tag.text.strip() and tag.name not in ['br', 'img', 'hr', 'input']:
            tag.decompose()
    
    # Get clean HTML
    cleaned = str(soup)
    
    # Extra compression: remove newlines and multiple spaces
    import re
    cleaned = re.sub(r'\s+', ' ', cleaned)  # collapse whitespace
    cleaned = cleaned.strip()
    
    return cleaned