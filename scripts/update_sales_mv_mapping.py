from pathlib import Path

p = r"C:\\Wellona\\wphAI\\web_modern\\app_v2.py"
s = Path(p).read_text(encoding="utf-8")

# Update comment
old_comment = """    Map sales_window to MV. Temp fallback until ops._sales_7d/_180d exist:
      7   -> ops._sales_15d (fallback)
      15  -> ops._sales_15d
      30  -> ops._sales_30d
      60  -> ops._sales_60d
      180 -> ops._sales_60d (fallback)"""

new_comment = """    Map sales_window to MV:
      7   -> ops._sales_7d
      15  -> ops._sales_15d
      30  -> ops._sales_30d
      60  -> ops._sales_60d
      180 -> ops._sales_180d"""

s = s.replace(old_comment, new_comment)

# Update logic
old_logic = """    if sales_window <= 10:
        return "ops._sales_15d"  # fallback for 7d until MV created
    elif sales_window <= 20:
        return "ops._sales_15d"
    elif sales_window <= 45:
        return "ops._sales_30d"
    elif sales_window <= 120:
        return "ops._sales_60d"
    else:
        return "ops._sales_60d"  # fallback for 180d until MV created"""

new_logic = """    if sales_window <= 10:
        return "ops._sales_7d"
    elif sales_window <= 20:
        return "ops._sales_15d"
    elif sales_window <= 45:
        return "ops._sales_30d"
    elif sales_window <= 120:
        return "ops._sales_60d"
    else:
        return "ops._sales_180d"  # 180+ days"""

s = s.replace(old_logic, new_logic)

Path(p).write_text(s, encoding="utf-8")
print("✅ Updated sales_window mapping: 7d and 180d MVs now active")
