import os
import shutil
import zipfile
import json
from datetime import datetime
from pathlib import Path
from database.db import get_connection, DB_PATH, get_setting, log_action

class BackupManager:
    def get_backup_dir(self):
        path = get_setting("backup_path", str(Path.home() / "alchemypos_backups"))
        os.makedirs(path, exist_ok=True)
        return path

    def create_backup(self, user_id, username, notes="Manual backup"):
        backup_dir = self.get_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alchemypos_backup_{timestamp}.zip"
        filepath = os.path.join(backup_dir, filename)

        try:
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(DB_PATH):
                    zf.write(DB_PATH, "alchemypos.db")
                meta = {
                    "created_at": datetime.now().isoformat(),
                    "created_by": username,
                    "notes": notes,
                    "db_path": DB_PATH,
                }
                zf.writestr("backup_meta.json", json.dumps(meta, indent=2))

            size = os.path.getsize(filepath)
            conn = get_connection()
            conn.execute("""INSERT INTO backups(filename,path,size_bytes,created_by,notes)
                            VALUES(?,?,?,?,?)""", (filename, filepath, size, user_id, notes))
            conn.commit()
            conn.close()
            log_action(user_id, username, "BACKUP_CREATE", f"Created backup: {filename}")
            return True, filepath, f"Backup created: {filename}"
        except Exception as e:
            return False, None, str(e)

    def restore_backup(self, backup_path, user_id, username):
        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                names = zf.namelist()
                if "alchemypos.db" not in names:
                    return False, "Invalid backup file."
                backup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_backup = DB_PATH + f".pre_restore_{backup_ts}"
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, pre_backup)
                zf.extract("alchemypos.db", os.path.dirname(DB_PATH))
            log_action(user_id, username, "BACKUP_RESTORE", f"Restored from: {backup_path}")
            return True, "Database restored. Please restart the application."
        except Exception as e:
            return False, str(e)

    def list_backups(self):
        conn = get_connection()
        rows = conn.execute("""SELECT b.*, u.username FROM backups b
                               LEFT JOIN users u ON u.id=b.created_by
                               ORDER BY b.created_at DESC""").fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["exists"] = os.path.exists(d["path"])
            result.append(d)
        return result

    def delete_backup(self, backup_id, user_id, username):
        conn = get_connection()
        row = conn.execute("SELECT path FROM backups WHERE id=?", (backup_id,)).fetchone()
        if not row:
            conn.close()
            return False, "Backup not found."
        try:
            if os.path.exists(row["path"]):
                os.remove(row["path"])
            conn.execute("DELETE FROM backups WHERE id=?", (backup_id,))
            conn.commit()
            log_action(user_id, username, "BACKUP_DELETE", f"Deleted backup_id={backup_id}")
            return True, "Backup deleted."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

backup_manager = BackupManager()
