import psycopg2
import psycopg2.extras
from config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def query(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        try:
            return list(cur.fetchall())
        except:
            return []
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        raise e
    finally:
        conn.close()
