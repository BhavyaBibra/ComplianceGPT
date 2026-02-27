import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY/SUPABASE_ANON_KEY must be set in environment.")
    exit(1)

supabase: Client = create_client(url, key)

print("Applying Supabase schema migrations...")

migration_sql = """
-- conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    evidence JSONB DEFAULT '[]',
    frameworks_used JSONB DEFAULT '[]',
    mapping_mode BOOLEAN DEFAULT FALSE,
    incident_mode BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
"""

try:
    # Use the RPC endpoint if we defined a run_sql function, or we can instruct the user to run it
    print("WARNING: Attempting to run via RPC `run_sql`. If this fails, you must run this manually in the Supabase SQL editor:")
    print("-" * 40)
    print(migration_sql)
    print("-" * 40)
    
    # Try calling a theoretical run_sql rpc. It usually doesn't exist by default.
    result = supabase.rpc("run_sql", {"sql": migration_sql}).execute()
    print("Migration successful via RPC:", result)
except Exception as e:
    print("Could not run migration via supabase python client (this is normal if no run_sql rpc exists).")
    print("\nACTION REQUIRED: Please copy the SQL block above and run it in your Supabase SQL Editor dashboard.")
