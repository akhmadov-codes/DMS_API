import os

def remove_bom(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    if content.startswith(b'\xef\xbb\xbf'):
        with open(file_path, 'wb') as f:
            f.write(content[3:])
        print(f"Tozalandi: {file_path}")

for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            remove_bom(os.path.join(root, file))
