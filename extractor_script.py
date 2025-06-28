import os

# Folder to search (change if needed)
search_dir = "."

# Get all .py files excluding this script itself
py_files = sorted([
    f for f in os.listdir(search_dir)
    if f.endswith(".py") and f != "list_scripts.py"
])

print("✅ Python files found:")
for f in py_files:
    print(f"- {f}")

print("\n🖥️ Use the following commands to run them all one by one:")

for f in py_files:
    print(f"python {f}")
