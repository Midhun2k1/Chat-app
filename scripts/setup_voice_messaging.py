import sys
import os

# Add workspace directory to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from sqlalchemy import text

def run_migrations():
    print("[Migration] Connecting to database...")
    try:
        with engine.connect() as conn:
            # 1. Add fld_message_type to tbl_messages
            print("[Migration] Checking fld_message_type column...")
            res_type_col = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tbl_messages' AND column_name='fld_message_type';"
            )).fetchone()
            if not res_type_col:
                print("[Migration] Adding fld_message_type column to tbl_messages...")
                conn.execute(text(
                    "ALTER TABLE tbl_messages ADD COLUMN fld_message_type VARCHAR(20) NOT NULL DEFAULT 'text';"
                ))
                conn.commit()
                print("[Migration] Column fld_message_type added.")
            else:
                print("[Migration] Column fld_message_type already exists.")

            # 2. Add fld_media_url to tbl_messages
            print("[Migration] Checking fld_media_url column...")
            res_url_col = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tbl_messages' AND column_name='fld_media_url';"
            )).fetchone()
            if not res_url_col:
                print("[Migration] Adding fld_media_url column to tbl_messages...")
                conn.execute(text(
                    "ALTER TABLE tbl_messages ADD COLUMN fld_media_url TEXT;"
                ))
                conn.commit()
                print("[Migration] Column fld_media_url added.")
            else:
                print("[Migration] Column fld_media_url already exists.")

            # 3. Add fld_duration_seconds to tbl_messages
            print("[Migration] Checking fld_duration_seconds column...")
            res_dur_col = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tbl_messages' AND column_name='fld_duration_seconds';"
            )).fetchone()
            if not res_dur_col:
                print("[Migration] Adding fld_duration_seconds column to tbl_messages...")
                conn.execute(text(
                    "ALTER TABLE tbl_messages ADD COLUMN fld_duration_seconds INTEGER;"
                ))
                conn.commit()
                print("[Migration] Column fld_duration_seconds added.")
            else:
                print("[Migration] Column fld_duration_seconds already exists.")

        print("[Migration] Voice messaging migrations completed successfully! [DONE]")
    except Exception as e:
        print(f"[Migration] Error during migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
