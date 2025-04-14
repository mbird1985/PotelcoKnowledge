from flask_login import UserMixin
from services.db import get_connection


class User(UserMixin):
    def __init__(self, id_or_username, by_username=False):
        conn = get_connection()
        c = conn.cursor()

        if by_username:
            c.execute("SELECT id, username, email, role, password FROM users WHERE username = ?", (id_or_username,))
        else:
            c.execute("SELECT id, username, email, role, password FROM users WHERE id = ?", (id_or_username,))

        result = c.fetchone()
        conn.close()

        if result:
            self.id = result[0]
            self.username = result[1]
            self.email = result[2]
            self.role = result[3]
            self.password_hash = result[4]
        else:
            self.id = None  # signals login failure

    def is_admin(self):
       return self.role == "admin"


    def verify_password(self, password_plain):
        """
        Compare a plain password to the stored hash.
        NOTE: Only works if you're using hashed passwords (bcrypt, werkzeug, etc.)
        """
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password_plain) if self.password_hash else False
    
    def has_role(self, *roles):
        return self.role in roles

