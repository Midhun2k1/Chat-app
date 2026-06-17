import sys
import os
from datetime import datetime, timezone

# Add workspace directory to python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from sqlalchemy import text

def run_migrations():
    print("[Migration] Connecting to database...")
    try:
        with engine.connect() as conn:
            # 1. Enable vector extension
            print("[Migration] Enabling vector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("[Migration] pgvector extension enabled successfully.")

            # 2. Add fld_is_bot to tbl_users
            print("[Migration] Checking tbl_users schema...")
            res_bot_col = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tbl_users' AND column_name='fld_is_bot';"
            )).fetchone()
            if not res_bot_col:
                print("[Migration] Adding fld_is_bot column to tbl_users...")
                conn.execute(text(
                    "ALTER TABLE tbl_users ADD COLUMN fld_is_bot BOOLEAN NOT NULL DEFAULT FALSE;"
                ))
                conn.commit()
                print("[Migration] Column fld_is_bot added.")
            else:
                print("[Migration] Column fld_is_bot already exists.")

            # 3. Add fld_embedding to tbl_messages
            print("[Migration] Checking tbl_messages schema...")
            res_embed_col = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='tbl_messages' AND column_name='fld_embedding';"
            )).fetchone()
            if not res_embed_col:
                print("[Migration] Adding fld_embedding column to tbl_messages...")
                conn.execute(text(
                    "ALTER TABLE tbl_messages ADD COLUMN fld_embedding vector(384);"
                ))
                conn.commit()
                print("[Migration] Column fld_embedding added.")
            else:
                print("[Migration] Column fld_embedding already exists.")

            # 4. Insert Bot Account if it doesn't exist
            print("[Migration] Checking if BuzzBee bot account exists...")
            res_bot_user = conn.execute(text(
                "SELECT fld_user_id FROM tbl_users WHERE fld_username = 'pingbee-ai';"
            )).fetchone()

            if not res_bot_user:
                print("[Migration] Inserting BuzzBee bot account...")
                # Insert the bot user with fld_user_id=999
                conn.execute(text("""
                    INSERT INTO tbl_users (
                        fld_user_id, fld_firstname, fld_lastname, fld_username,
                        fld_hashed_password, fld_is_active, fld_is_verified, fld_is_bot,
                        fld_created_at
                    ) VALUES (
                        999, 'Buzz', ' ', 'pingbee-ai',
                        '$2b$12$BOTACCOUNTNOLOGINALLOWED',
                        TRUE, TRUE, TRUE, NOW()
                    );
                """))
                conn.commit()
                print("[Migration] Buzz bot account created with ID 999. [OK]")
            else:
                # Ensure it is marked as bot
                print("[Migration] Bot account already exists, ensuring fld_is_bot=TRUE...")
                conn.execute(text(
                    "UPDATE tbl_users SET fld_is_bot = TRUE WHERE fld_username = 'pingbee-ai';"
                ))
                conn.commit()
                print("[Migration] Buzz bot account verified. [OK]")

        print("[Migration] All migrations completed successfully! [DONE]")
    except Exception as e:
        print(f"[Migration] Error during migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
