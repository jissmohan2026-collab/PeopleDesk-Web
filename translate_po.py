import re
import time
from deep_translator import GoogleTranslator

po_file = 'translations/ml/LC_MESSAGES/messages.po'

with open(po_file, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find msgid "..." and replace the following msgstr "" with msgstr "translated"
# A simple approach is to iterate line by line
lines = content.split('\n')
new_lines = []

translator = GoogleTranslator(source='en', target='ml')

current_msgid = ""
is_msgid = False
is_msgstr = False

for i, line in enumerate(lines):
    if line.startswith('msgid "'):
        # extract string
        current_msgid = line[7:-1]
        is_msgid = True
        new_lines.append(line)
    elif line.startswith('msgstr "') and current_msgid:
        if current_msgid == "":
            new_lines.append(line)
        else:
            try:
                # avoid translating things that look like variables or pure html
                if '{' in current_msgid or '<' in current_msgid:
                    translated = current_msgid
                else:
                    translated = translator.translate(current_msgid)
                    time.sleep(0.1) # rate limiting
                new_lines.append(f'msgstr "{translated}"')
            except Exception as e:
                print(f"Failed to translate: {current_msgid}")
                new_lines.append(f'msgstr "{current_msgid}"')
        current_msgid = ""
    else:
        new_lines.append(line)

with open(po_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Translation completed.")
