#! /usr/bin/python3
if __name__ == '__main__':
  import trabalho.db as db
  import sys
  if len(sys.argv) != 2:
    print("Expected table name as argument")
    sys.exit(1)
  db.connect()
  data = db.execute('SELECT * FROM ' + sys.argv[1]).fetchall()
  print("%d results ..." % len(data))
  for d in data: 
     print([ (c,d[c]) for c in d.keys()]) 
  db.close()
