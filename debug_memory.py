
import mlx_embeddings
import database
import sys

print("1. Testing Embedding Generation...")
try:
    emb = mlx_embeddings.get_embedding("test memory")
    if emb and len(emb) > 0:
        print(f"✅ Embedding generated (len={len(emb)})")
    else:
        print("❌ Embedding generation failed (returned empty list)")
except Exception as e:
    print(f"❌ Embedding crashed: {e}")

print("\n2. Testing Database Insert...")
try:
    note_id = database.add_note("DeBug Memory Test", emb if emb else [])
    print(f"✅ Note saved with ID: {note_id}")
    
    # Verify retrieval
    print("   Verifying retrieval...")
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    if row:
        print(f"   ✅ Note found in DB: {dict(row)}")
        # Cleaning up
        database.delete_note(note_id)
        print("   ✅ Test note cleaned up.")
    else:
        print("   ❌ Note NOT found in DB after insert.")
    conn.close()

except Exception as e:
    print(f"❌ Database error: {e}")
