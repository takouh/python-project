from app import create_app, db
from app.models import User, Listing
import os

app = create_app()

# Database initialization is handled within create_app() via its initialize_app hook

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
