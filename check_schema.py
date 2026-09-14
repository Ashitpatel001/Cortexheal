import psycopg2
conn = psycopg2.connect('postgresql://cortexheal:cortexpassword@localhost:5433/cortexheal_db')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
for row in cur.fetchall():
    print(row[0])
conn.close()
