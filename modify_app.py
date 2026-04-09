import re

with open('app.py', 'r') as f:
    content = f.read()

# Pattern matches ctk.CTk(OptionMenu|CheckBox|Switch|RadioButton|ComboBox)(self.parent_name, ...
pattern = r'(ctk\.CTk(?:OptionMenu|CheckBox|Switch|RadioButton|ComboBox)\([^,]+,\s*)'
replacement = r'\g<1>cursor="hand2", '

new_content = re.sub(pattern, replacement, content)

with open('app.py', 'w') as f:
    f.write(new_content)

print("Modification complete.")
