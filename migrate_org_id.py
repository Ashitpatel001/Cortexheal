import psycopg2
conn = psycopg2.connect('postgresql://cortexheal:cortexpassword@localhost:5433/cortexheal_db')
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE runs ADD COLUMN org_id VARCHAR(100) DEFAULT 'default_org'")
except psycopg2.errors.DuplicateColumn:
    conn.rollback()
else:
    conn.commit()

try:
    cur.execute("ALTER TABLE incidents ADD COLUMN org_id VARCHAR(100) DEFAULT 'default_org'")
except psycopg2.errors.DuplicateColumn:
    conn.rollback()
else:
    conn.commit()

conn.close()
