from datetime import datetime, timedelta
from database.db import get_connection, verify_password, hash_password, log_action

MAX_ATTEMPTS    = 5
LOCKOUT_MINUTES = 15

class AuthManager:
    def __init__(self):
        self.current_user = None

    def login(self, username, password):
        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
        if not user:
            conn.close()
            return False, "Invalid username or password."

        if user["locked_until"]:
            lock_time = datetime.fromisoformat(user["locked_until"])
            if datetime.now() < lock_time:
                remaining = int((lock_time - datetime.now()).total_seconds() / 60) + 1
                conn.close()
                return False, f"Account locked. Try again in {remaining} minute(s)."
            conn.execute("UPDATE users SET locked_until=NULL,failed_attempts=0 WHERE id=?",
                         (user["id"],)); conn.commit()

        if not verify_password(password, user["password_hash"]):
            attempts = user["failed_attempts"] + 1
            if attempts >= MAX_ATTEMPTS:
                lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                conn.execute("UPDATE users SET failed_attempts=?,locked_until=? WHERE id=?",
                             (attempts, lock_until, user["id"])); conn.commit(); conn.close()
                return False, f"Too many attempts. Account locked for {LOCKOUT_MINUTES} minutes."
            conn.execute("UPDATE users SET failed_attempts=? WHERE id=?",
                         (attempts, user["id"])); conn.commit(); conn.close()
            return False, f"Invalid password. {MAX_ATTEMPTS - attempts} attempt(s) remaining."

        conn.execute("UPDATE users SET failed_attempts=0,locked_until=NULL,last_login=? WHERE id=?",
                     (datetime.now().isoformat(), user["id"])); conn.commit(); conn.close()
        self.current_user = {
            "id":        user["id"],
            "username":  user["username"],
            "role":      user["role"],
            "full_name": user["full_name"] or user["username"],
        }
        log_action(user["id"], user["username"], "LOGIN", "Successful login")
        return True, "Login successful."

    def logout(self):
        if self.current_user:
            log_action(self.current_user["id"], self.current_user["username"], "LOGOUT", "")
        self.current_user = None

    def is_admin(self):
        return self.current_user and self.current_user["role"] == "admin"

    def is_inventory_manager(self):
        return self.current_user and self.current_user["role"] == "inventory_manager"

    def can_access_inventory(self):
        return self.current_user and self.current_user["role"] in ("admin","inventory_manager")

    def change_password(self, user_id, new_password):
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters."
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                     (hash_password(new_password), user_id))
        conn.commit(); conn.close()
        log_action(user_id, "self", "PASSWORD_CHANGE", "")
        return True, "Password changed."

    def get_all_users(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT id,username,role,full_name,is_active,created_at,last_login FROM users ORDER BY role,username"
        ).fetchall(); conn.close()
        return [dict(r) for r in rows]

    def add_user(self, username, password, role, full_name):
        if len(username) < 3: return False, "Username must be at least 3 characters."
        if len(password) < 6: return False, "Password must be at least 6 characters."
        if role not in ("admin","cashier","inventory_manager"): return False, "Invalid role."
        conn = get_connection()
        if conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
            conn.close(); return False, "Username already exists."
        conn.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",
                     (username, hash_password(password), role, full_name))
        conn.commit(); conn.close()
        return True, "User created successfully."

    def update_user(self, user_id, full_name, role, is_active):
        conn = get_connection()
        conn.execute("UPDATE users SET full_name=?,role=?,is_active=? WHERE id=?",
                     (full_name, role, is_active, user_id))
        conn.commit(); conn.close()
        return True, "User updated."

    def delete_user(self, user_id, requesting_user_id):
        if user_id == requesting_user_id: return False, "Cannot delete your own account."
        conn = get_connection()
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit(); conn.close()
        return True, "User deleted."

    def reset_user_password(self, user_id, new_password, admin_id, admin_username):
        if len(new_password) < 6: return False, "Password must be at least 6 characters."
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash=?,failed_attempts=0,locked_until=NULL WHERE id=?",
                     (hash_password(new_password), user_id))
        conn.commit(); conn.close()
        log_action(admin_id, admin_username, "PASSWORD_RESET", f"user_id={user_id}")
        return True, "Password reset successfully."

    # ── Security questions (supports 1–3) ───────────────────────────────────
    def set_security_question(self, user_id, question, answer):
        """Backwards-compat: save single question."""
        if not question or not answer: return False, "Question and answer required."
        conn = get_connection()
        conn.execute("UPDATE users SET security_question=?,security_answer_hash=? WHERE id=?",
                     (question, hash_password(answer.strip().lower()), user_id))
        conn.commit(); conn.close()
        return True, "Security question saved."

    def set_security_questions(self, user_id, questions, answers):
        """Save up to 3 security questions for a user."""
        if not questions or not answers: return False, "Questions and answers required."
        cols = [
            ("security_question",  "security_answer_hash"),
            ("security_question2", "security_answer2_hash"),
            ("security_question3", "security_answer3_hash"),
        ]
        conn = get_connection()
        for i, (qcol, acol) in enumerate(cols):
            q = questions[i] if i < len(questions) else None
            a = answers[i].strip().lower() if i < len(answers) and answers[i].strip() else None
            if q and a:
                conn.execute(f"UPDATE users SET {qcol}=?,{acol}=? WHERE id=?",
                             (q, hash_password(a), user_id))
        conn.commit(); conn.close()
        return True, "Security questions saved."

    def get_security_question(self, username):
        """Backwards-compat: return first security question."""
        qs = self.get_security_questions(username)
        return qs[0] if qs else None

    def get_security_questions(self, username):
        """Return list of security questions set for the user (1–3)."""
        conn = get_connection()
        row = conn.execute(
            """SELECT security_question, security_question2, security_question3
               FROM users WHERE username=?""", (username,)).fetchone()
        conn.close()
        if not row: return []
        return [q for q in (row[0], row[1], row[2]) if q]

    def verify_security_answer(self, username, answer):
        """Backwards-compat: verify first answer only."""
        conn = get_connection()
        row = conn.execute("SELECT security_answer_hash FROM users WHERE username=?",
                           (username,)).fetchone()
        conn.close()
        if not row or not row[0]: return False
        return verify_password(answer.strip().lower(), row[0])

    def verify_security_answers(self, username, answers):
        """Verify all provided answers (must all match in order)."""
        conn = get_connection()
        row = conn.execute(
            """SELECT security_answer_hash, security_answer2_hash, security_answer3_hash
               FROM users WHERE username=?""", (username,)).fetchone()
        conn.close()
        if not row: return False
        hashes = [h for h in (row[0], row[1], row[2]) if h]
        if len(answers) < len(hashes): return False
        return all(
            verify_password(answers[i].strip().lower(), h)
            for i, h in enumerate(hashes)
        )

    def reset_own_password(self, username, new_password):
        if len(new_password) < 6: return False, "Password must be at least 6 characters."
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash=?,failed_attempts=0,locked_until=NULL WHERE username=?",
                     (hash_password(new_password), username))
        conn.commit(); conn.close()
        return True, "Password reset successfully."

auth = AuthManager()
