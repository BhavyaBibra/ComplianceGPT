import { useEffect, useState } from 'react';
import { supabase } from './lib/supabase';
import { Auth } from './components/Auth';
import { Sidebar } from './components/Sidebar';
import { ChatWorkspace } from './components/ChatWorkspace';
import type { Session } from '@supabase/supabase-js';

function App() {
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
        });

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
        });

        return () => subscription.unsubscribe();
    }, []);

    if (loading) {
        return (
            <div className="flex h-screen w-screen items-center justify-center bg-bg-color text-text-primary">
                <div className="animate-pulse">Loading ComplianceGPT...</div>
            </div>
        );
    }

    if (!session) {
        return <Auth />;
    }

    return (
        <div className="app-container">
            <Sidebar />
            <ChatWorkspace />
        </div>
    );
}

export default App;
