import re

with open("app.py", "r") as f:
    lines = f.readlines()

new_lines = []
targets = ["ctk.CTkOptionMenu", "ctk.CTkComboBox", "ctk.CTkCheckBox", "ctk.CTkRadioButton", "ctk.CTkSwitch"]

for line in lines:
    for w in targets:
        if w + "(" in line and 'cursor="hand2"' not in line:
            # Find the match
            match = re.search(r'(' + re.escape(w) + r'\([^,)]+)(,?)', line)
            if match:
                if match.group(2) == ',':
                    # Has a comma, insert after it
                    line = line[:match.end()] + ' cursor="hand2",' + line[match.end():]
                else:
                    # No comma, insert before the closing paren if we can find it
                    # Or maybe just append it with a comma
                    paren_idx = line.find(')', match.end())
                    if paren_idx != -1:
                        line = line[:paren_idx] + ', cursor="hand2"' + line[paren_idx:]
    new_lines.append(line)

with open("app.py", "w") as f:
    f.writelines(new_lines)
