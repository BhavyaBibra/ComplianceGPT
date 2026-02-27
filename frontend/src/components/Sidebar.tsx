import { LogOut, Shield } from 'lucide-react';
import { supabase } from '../lib/supabase';

export function Sidebar() {
    const handleLogout = async () => {
        await supabase.auth.signOut();
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h1 className="sidebar-title">
                    <Shield size={24} className="text-accent-color" />
                    ComplianceGPT
                </h1>
                <p className="sidebar-subtitle">Cybersecurity Compliance Copilot</p>
            </div>

            <div className="sidebar-spacer" />

            <button onClick={handleLogout} className="logout-button">
                <LogOut size={16} />
                Sign Out
            </button>
        </aside>
    );
}
