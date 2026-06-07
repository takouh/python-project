from app import create_app, db
from sqlalchemy import text

app = create_app()

def test_connection():
    with app.app_context():
        print("Checking database connection...")
        try:
            # 1. Test the raw connection by running a simple SQL query
            result = db.session.execute(text("SELECT version();")).fetchone()
            print("\n✅ SUCCESS: Connected to PostgreSQL!")
            print(f"Database Version: {result[0]}\n")
            
            # 2. Check if your tables (User and Listing) exist
            # Note: Depending on your SQLAlchemy version, this inspects the database
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print("Found the following tables in your database:")
            if tables:
                for table in tables:
                    print(f" - {table}")
                print("\n🎉 If you see 'user' and 'listing' above, pgAdmin will see them too!")
            else:
                print(" ⚠️ No tables found. Your initialization hook might not have run yet.")
                print(" Try running your main 'run.py' script first to generate them.")

        except Exception as e:
            print("\n❌ CONNECTION FAILED!")
            print(f"Error details: {e}")
            print("\nDouble-check that:")
            print("1. Your PostgreSQL server is actually running.")
            print("2. Your .env file has the exact correct username, password, and DB name.")
            print("3. You installed psycopg2-binary ('pip install psycopg2-binary').")

if __name__ == '__main__':
    test_connection()