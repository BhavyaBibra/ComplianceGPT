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
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const submitQuery = async (question: string, frameworks?: string[]): Promise<QueryResponse> => {
    const body: any = { question };
    if (frameworks && frameworks.length > 0) {
        body.frameworks = frameworks;
    }

    const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });

    if (!res.ok) {
        throw new Error(`API error: ${res.statusText}`);
    }

    return res.json();
};

export async function generateReport(reportType: string, messages: ChatMessage[]): Promise<{ markdown: string }> {
    const response = await fetch(`${API_BASE}/api/report`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
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
    onError?: (error: Error) => void;
    onComplete?: () => void;
}

export const submitQueryStream = async (question: string, frameworks: string[] | undefined, callbacks: StreamCallbacks) => {
    const body: any = { question, stream: true };
    if (frameworks && frameworks.length > 0) {
        body.frameworks = frameworks;
    }

    try {
        const res = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
