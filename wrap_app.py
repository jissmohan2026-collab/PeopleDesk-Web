import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# flash('Message', 'category') -> flash(_('Message'), 'category')
# or flash("Message", "category") -> flash(_("Message"), "category")
def repl_flash(match):
    msg = match.group(2)
    # Check if already wrapped
    if match.group(1).endswith('(_('):
        return match.group(0)
    
    quote = match.group(3)
    rest = match.group(4)
    
    # We want to replace flash('message', ...) with flash(_('message'), ...)
    # match.group(1) is 'flash('
    # match.group(2) is the message without quotes
    return f"{match.group(1)}_({quote}{msg}{quote}){rest}"

content = re.sub(r'(flash\s*\(\s*)([\'"])(.*?)\2(\s*,\s*[\'"].*?[\'"]\s*\))', repl_flash, content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Processed app.py")
