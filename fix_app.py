import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

def fix_flash(match):
    # match.group(0) is like flash(_(No consignment found with that tracking ID.'No consignment found with that tracking ID.), 'danger')
    text = match.group(1) # The text inside
    rest = match.group(2) # The rest
    # We want flash(_('text'), rest
    # If it ends with quote, extract the string correctly
    # actually let's just grab everything after the quote
    
    # We can split by single quote
    parts = match.group(0).split("'")
    if len(parts) >= 3:
        clean_msg = parts[1]
        category = parts[3]
        return f"flash(_('{clean_msg}'), '{category}')"
    return match.group(0)

# We will match flash(_( ... ), ' ... ')
content = re.sub(r'flash\(_\((.*?)\),\s*[\'"](.*?)[\'"]\)', fix_flash, content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed app.py")
