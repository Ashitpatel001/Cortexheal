
with open("cortexheal/server/api.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("Depends(verify_api_key)", "Depends(get_current_user)")

with open("cortexheal/server/api.py", "w", encoding="utf-8") as f:
    f.write(content)

