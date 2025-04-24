from flask_login import UserMixin
from db.db import get_db
import sqlite3

class User(UserMixin):
    def __init__(self, id, name, email, profile_info=None, campus_id=None):
        self.id = id
        self.name = name
        self.email = email
        self.profile_info = profile_info
        self.campus_id = campus_id

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        try:
            db = get_db()
            user_row = db.execute(
                'SELECT id, name, email, profile_info, campus_id FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            if user_row:
                return User(id=user_row['id'], name=user_row['name'], email=user_row['email'], profile_info=user_row['profile_info'], campus_id=user_row['campus_id'])
            return None
        except sqlite3.Error as e:
            print(f"Database error fetching user {user_id}: {e}")
            return None