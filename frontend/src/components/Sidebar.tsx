import { useEffect, useState } from 'react';
import { LogOut, Shield, Plus, MessageSquare } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { fetchConversations, type Conversation } from '../lib/api';

interface SidebarProps {
    activeId: string | null;
    onSelect: (id: string | null) => void;
    triggerRefetch: number;
}

export function Sidebar({ activeId, onSelect, triggerRefetch }: SidebarProps) {
    const [conversations, setConversations] = useState<Conversation[]>([]);

    useEffect(() => {
        fetchConversations()
            .then(setConversations)
            .catch(err => console.error("Failed to load sidebar", err));
    }, [triggerRefetch]);
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
                <p className="sidebar-subtitle">Cybersecurity Copilot</p>
            </div>

            <button
                className="sidebar-new-chat-btn"
                onClick={() => onSelect(null)}
            >
                <Plus size={16} />
                New Chat
            </button>

            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
                {conversations.map(conv => (
                    <button
                        key={conv.id}
                        onClick={() => onSelect(conv.id)}
                        className={`sidebar-chat-item ${activeId === conv.id ? 'active' : ''}`}
                        title={conv.title}
                    >
                        <MessageSquare size={16} className="shrink-0" />
                        <span className="truncate">{conv.title}</span>
                    </button>
                ))}
            </div>

            <button onClick={handleLogout} className="logout-button mt-auto">
                <LogOut size={16} />
                Sign Out
            </button>
        </aside>
    );
}
