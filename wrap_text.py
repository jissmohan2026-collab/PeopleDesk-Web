import os
import re

def wrap_text_in_templates(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace >Text<
                def repl_tag(match):
                    text = match.group(1)
                    if not text.strip() or '{%' in text or '{{' in text or '}}' in text or '%}' in text:
                        return match.group(0)
                    if not re.search(r'[a-zA-Z]', text):
                        return match.group(0)
                        
                    # skip if it looks like javascript or css
                    if 'function' in text or 'var ' in text or 'const ' in text or 'margin:' in text or 'padding:' in text:
                        return match.group(0)

                    stripped = text.strip()
                    start_idx = text.find(stripped)
                    end_idx = start_idx + len(stripped)
                    prefix = text[:start_idx]
                    suffix = text[end_idx:]
                    escaped_stripped = stripped.replace("'", "\\'")
                    wrapped = f"{{{{ _('{escaped_stripped}') }}}}"
                    return f">{prefix}{wrapped}{suffix}<"

                content = re.sub(r'>([^<]+)<', repl_tag, content)
                
                # Replace placeholder="Text"
                def repl_placeholder(match):
                    attr = match.group(1) # placeholder or title
                    quote = match.group(2)
                    text = match.group(3)
                    
                    if not text.strip() or '{%' in text or '{{' in text:
                        return match.group(0)
                    if not re.search(r'[a-zA-Z]', text):
                        return match.group(0)
                        
                    escaped_stripped = text.replace("'", "\\'")
                    wrapped = f"{{{{ _('{escaped_stripped}') }}}}"
                    return f'{attr}={quote}{wrapped}{quote}'

                content = re.sub(r'(placeholder|title)=([\'"])([^\'"]+)\2', repl_placeholder, content)

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Processed {path}")

if __name__ == '__main__':
    wrap_text_in_templates('templates')
