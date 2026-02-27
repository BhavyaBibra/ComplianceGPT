import { useEffect, useState } from 'react';
import { LogOut, Shield, Plus, MessageSquare, Trash2 } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { fetchConversations, deleteConversation, type Conversation } from '../lib/api';

interface SidebarProps {
    activeId: string | null;
    onSelect: (id: string | null) => void;
    triggerRefetch: number;
}

function getDateGroup(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    if (date >= today) return 'Today';
    if (date >= yesterday) return 'Yesterday';
    if (date >= sevenDaysAgo) return 'Previous 7 Days';
    if (date >= thirtyDaysAgo) return 'Previous 30 Days';
    return 'Older';
}

function groupConversationsByDate(conversations: Conversation[]): Record<string, Conversation[]> {
    const groups: Record<string, Conversation[]> = {};
    const order = ['Today', 'Yesterday', 'Previous 7 Days', 'Previous 30 Days', 'Older'];

    for (const conv of conversations) {
        const group = getDateGroup(conv.updated_at || conv.created_at);
        if (!groups[group]) groups[group] = [];
        groups[group].push(conv);
    }

    // Return in defined order, only groups that have items
    const ordered: Record<string, Conversation[]> = {};
    for (const key of order) {
        if (groups[key] && groups[key].length > 0) {
            ordered[key] = groups[key];
        }
    }
    return ordered;
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

    const handleDelete = async (e: React.MouseEvent, convId: string) => {
        e.stopPropagation();
        try {
            await deleteConversation(convId);
            setConversations(prev => prev.filter(c => c.id !== convId));
            if (activeId === convId) {
                onSelect(null);
            }
        } catch (err) {
            console.error("Failed to delete conversation:", err);
        }
    };

    const grouped = groupConversationsByDate(conversations);

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h1 className="sidebar-title">
                    <Shield size={20} />
                    ComplianceGPT
                </h1>
                <p className="sidebar-subtitle">Cybersecurity Copilot</p>
            </div>

            <button className="sidebar-new-chat-btn" onClick={() => onSelect(null)}>
                <Plus size={16} />
                <span>New Chat</span>
            </button>

            <div className="sidebar-conversations-list">
                {Object.entries(grouped).map(([dateLabel, convs]) => (
                    <div key={dateLabel} className="sidebar-date-group">
                        <div className="sidebar-date-label">{dateLabel}</div>
                        {convs.map(conv => (
                            <div
                                key={conv.id}
                                className={`sidebar-chat-item-wrapper ${activeId === conv.id ? 'active' : ''}`}
                                onClick={() => onSelect(conv.id)}
                            >
                                <MessageSquare size={16} className="sidebar-chat-icon" />
                                <span className="sidebar-chat-title">{conv.title}</span>
                                <button
                                    className="sidebar-delete-btn"
                                    onClick={(e) => handleDelete(e, conv.id)}
                                    title="Delete conversation"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            <button onClick={handleLogout} className="logout-button">
                <LogOut size={16} />
                Sign Out
            </button>
        </aside>
    );
}
