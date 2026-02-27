export interface RetrievedChunk {
    chunk: string;
    framework: string;
    similarity: number;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: string[];
    evidence?: RetrievedChunk[];
    frameworks_used?: string[];
    mapping_mode?: boolean;
    incident_mode?: boolean;
}

export interface QueryResponse {
    answer: string;
    citations: string[];
    frameworks_used: string[];
    mapping_mode?: boolean;
    incident_mode?: boolean;
    retrieved_chunks: RetrievedChunk[];
    conversation_id?: string;
}

export interface Conversation {
    id: string;
    user_id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

import { supabase } from './supabase';

async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export const submitQuery = async (question: string, frameworks?: string[], conversation_id?: string | null): Promise<QueryResponse> => {
    const body: any = { question };
    if (frameworks && frameworks.length > 0) {
        body.frameworks = frameworks;
    }
    if (conversation_id) {
        body.conversation_id = conversation_id;
    }

    const headers = {
        'Content-Type': 'application/json',
        ...(await getAuthHeaders())
    };

    const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        throw new Error(`API error: ${res.statusText}`);
    }

    return res.json();
};

export async function generateReport(reportType: string, messages: ChatMessage[]): Promise<{ markdown: string }> {
    const headers = {
        'Content-Type': 'application/json',
        ...(await getAuthHeaders())
    };

    const response = await fetch(`${API_BASE}/api/report`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
            report_type: reportType,
            messages: messages.map(m => ({
                role: m.role,
                content: m.content,
                citations: m.citations,
                frameworks_used: m.frameworks_used
            }))
        }),
    });

    if (!response.ok) {
        throw new Error(`Report generation failed: ${response.statusText}`);
    }

    return await response.json() as { markdown: string };
};

export interface StreamCallbacks {
    onMetadata?: (data: Omit<QueryResponse, 'answer'>) => void;
    onToken?: (token: string) => void;
    onConversationId?: (id: string) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
}

export const submitQueryStream = async (question: string, frameworks: string[] | undefined, conversation_id: string | null, callbacks: StreamCallbacks) => {
    const body: any = { question, stream: true };
    if (frameworks && frameworks.length > 0) {
        body.frameworks = frameworks;
    }
    if (conversation_id) {
        body.conversation_id = conversation_id;
    }

    try {
        const headers = {
            'Content-Type': 'application/json',
            ...(await getAuthHeaders())
        };

        const res = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            throw new Error(`API error: ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        const decoder = new TextDecoder('utf-8');

        if (!reader) throw new Error("No reader available");

        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim() === '') continue;
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6);
                    if (dataStr === '[DONE]') {
                        callbacks.onComplete?.();
                        return;
                    }
                    try {
                        const parsed = JSON.parse(dataStr);
                        if (parsed.type === 'metadata') {
                            callbacks.onMetadata?.(parsed.data);
                        } else if (parsed.type === 'content') {
                            callbacks.onToken?.(parsed.text);
                        } else if (parsed.type === 'conversation_id') {
                            callbacks.onConversationId?.(parsed.id);
                        } else if (parsed.type === 'done') {
                            callbacks.onComplete?.();
                            return;
                        }
                    } catch (e) {
                        console.error("Error parsing stream chunk", e, dataStr);
                    }
                }
            }
        }
        callbacks.onComplete?.();
    } catch (err: any) {
        callbacks.onError?.(err);
    }
};

export async function fetchConversations(): Promise<Conversation[]> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/conversations`, { headers });
    if (!res.ok) throw new Error("Failed to fetch conversations");
    return res.json();
}

export async function fetchConversationDetail(id: string): Promise<Conversation & { messages: ChatMessage[] }> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/conversations/${id}`, { headers });
    if (!res.ok) throw new Error("Failed to fetch conversation detail");
    return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/conversations/${id}`, { method: 'DELETE', headers });
    if (!res.ok) throw new Error("Failed to delete conversation");
}
