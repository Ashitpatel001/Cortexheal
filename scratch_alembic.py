
with open("migrations/versions/121e2261b242_add_org_id_and_extend_fingerprint_to_.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("down_revision: Union[str, None] = None", "down_revision: Union[str, None] = \"77225d008f23\"")

with open("migrations/versions/121e2261b242_add_org_id_and_extend_fingerprint_to_.py", "w", encoding="utf-8") as f:
    f.write(content)

