import urllib.request
import urllib.parse
import json
import time

po_file = 'translations/ml/LC_MESSAGES/messages.po'

with open(po_file, 'r', encoding='utf-8') as f:
    content = f.read()

def translate_text(text, sl='en', tl='ml'):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=" + sl + "&tl=" + tl + "&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res = response.read().decode('utf-8')
            data = json.loads(res)
            return "".join([part[0] for part in data[0]])
    except Exception as e:
        print("Error translating:", text, e)
        return text

lines = content.split('\n')
new_lines = []

current_msgid = ""

for i, line in enumerate(lines):
    if line.startswith('msgid "'):
        current_msgid = line[7:-1]
        new_lines.append(line)
    elif line.startswith('msgstr "') and current_msgid != "":
        if current_msgid.strip() == "":
            new_lines.append(line)
        elif '{' in current_msgid or '<' in current_msgid or '_' in current_msgid:
            new_lines.append(f'msgstr "{current_msgid}"')
        else:
            translated = translate_text(current_msgid)
            translated = translated.replace('"', '\\"')
            new_lines.append(f'msgstr "{translated}"')
            time.sleep(0.05)
        current_msgid = ""
    else:
        new_lines.append(line)

with open(po_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Translation completed.")
