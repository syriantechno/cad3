import os, re

icon_dir = "frontend/icons"
for fname in os.listdir(icon_dir):
    if not fname.lower().endswith(".svg"):
        continue
    path = os.path.join(icon_dir, fname)
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()

    # تأكد وجود fill في كل path
    data = re.sub(r'fill="none"', 'fill="#000000"', data)
    # تأكد من أن كل stroke يتم تحويله إلى fill
    data = re.sub(r'stroke="[^"]+"', 'fill="#000000"', data)
    # لو مافي أي fill نهائياً، ضيف واحد افتراضي
    if 'fill=' not in data:
        data = data.replace('<path', '<path fill="#000000"')

    # لو مافيه viewBox، أضف واحد بسيط
    if 'viewBox' not in data:
        data = re.sub(r'<svg([^>]*)>', r'<svg\1 viewBox="0 0 100 100">', data)

    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"[FIXED] {fname}")
