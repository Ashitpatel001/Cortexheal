from cortexheal.storage.postgres import get_connection
cur = get_connection().__enter__().cursor()
cur.execute('SELECT column_name, data_type FROM information_schema.columns WHERE table_name = \'runs\'')
print(cur.fetchall())