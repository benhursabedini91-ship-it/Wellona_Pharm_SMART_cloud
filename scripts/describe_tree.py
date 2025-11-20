import os
import sys

WPH_ROOT = r"C:\Wellona\WPHAI"

def tree(directory, prefix="", file=sys.stdout):
    contents = sorted(os.listdir(directory))
    pointers = ["├── "] * (len(contents) - 1) + ["└── "]
    for pointer, path in zip(pointers, contents):
        full_path = os.path.join(directory, path)
        if os.path.isdir(full_path):
            print(f"{prefix}{pointer}{path}\\", file=file)
            extension = "│   " if pointer == "├── " else "    "
            tree(full_path, prefix=prefix + extension, file=file)
        else:
            print(f"{prefix}{pointer}{path}", file=file)

if __name__ == "__main__":
    output_path = r"C:\Wellona\WPHAI\logs\structure.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # ✅ krijon logs nëse mungon
    with open(output_path, "w", encoding="utf-8") as f:
        print(WPH_ROOT + "\\", file=f)
        tree(WPH_ROOT, file=f)
    print(f"✅ Strukturë e ruajtur në: {output_path}")
