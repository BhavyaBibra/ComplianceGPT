import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, AlertCircle, Info, FileText, Shield } from 'lucide-react';
import { MessageItem } from './MessageItem';
import { submitQueryStream, fetchConversationDetail, type ChatMessage } from '../lib/api';
import { ReportModal } from './ReportModal';

const FRAMEWORK_OPTIONS = [
    { id: 'nist80053', label: 'NIST 800-53' },
    { id: 'iso27001', label: 'ISO 27001' },
    { id: 'nistcsf', label: 'NIST CSF' }
];

interface ChatWorkspaceProps {
    activeId: string | null;
    onNewConversation: (id: string) => void;
}

export function ChatWorkspace({ activeId, onNewConversation }: ChatWorkspaceProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isFetchingHistory, setIsFetchingHistory] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // All selected by default
    const [selectedFrameworks, setSelectedFrameworks] = useState<Set<string>>(
        new Set(FRAMEWORK_OPTIONS.map(fw => fw.id))
    );
    const [isReportModalOpen, setIsReportModalOpen] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, loading]);

    useEffect(() => {
        if (!activeId) {
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: 'Hello! I am ComplianceGPT, your GenAI cybersecurity compliance copilot. Ask me questions about NIST 800-53, ISO 27001, and more.',
            }]);
            return;
        }

        setIsFetchingHistory(true);
        fetchConversationDetail(activeId)
            .then(data => {
                setMessages(data.messages || []);
            })
            .catch(err => {
                console.error("Failed to fetch history:", err);
                setError("Failed to fetch conversation history.");
            })
            .finally(() => setIsFetchingHistory(false));
    }, [activeId]);

    const handleSend = async () => {
        if (!input.trim() || loading || isFetchingHistory) return;

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
        };

        const assistantMsgId = (Date.now() + 1).toString();

        setMessages((prev) => [...prev, userMsg, {
            id: assistantMsgId,
            role: 'assistant',
            content: ''
        }]);

        setInput('');
        setLoading(true);
        setError(null);

        try {
            const frameworksArr = Array.from(selectedFrameworks);

            await submitQueryStream(userMsg.content, frameworksArr, activeId, {
                onMetadata: (data) => {
                    setMessages((prev) => prev.map(msg =>
                        msg.id === assistantMsgId ? {
                            ...msg,
                            citations: data.citations,
                            frameworks_used: data.frameworks_used,
                            evidence: data.retrieved_chunks,
                            mapping_mode: data.mapping_mode,
                            incident_mode: data.incident_mode
                        } : msg
                    ));
                    setLoading(false); // Done gathering evidence
                },
                onToken: (token) => {
                    setMessages((prev) => prev.map(msg =>
                        msg.id === assistantMsgId ? { ...msg, content: msg.content + token } : msg
                    ));
                },
                onConversationId: (id) => {
                    onNewConversation(id);
                },
                onError: (err) => {
                    console.error(err);
                    setError(err.message || 'Streaming failed.');
                    setLoading(false);
                },
                onComplete: () => {
                    setLoading(false); // Backup termination
                }
            });
        } catch (err: any) {
            console.error(err);
            setError(err.message || 'Failed to connect to backend API.');
            setLoading(false);
        } finally {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <main className="chat-workspace">
            <header className="chat-header">
                <div className="header-title-container">
                    <Shield size={24} className="text-accent-color" />
                    <h1 className="header-title">ComplianceGPT</h1>
                </div>
                <button
                    className="generate-report-btn"
                    onClick={() => setIsReportModalOpen(true)}
                    title="Synthesize conversation into a structured markdown report"
                >
                    <FileText size={16} />
                    <span>Generate Report</span>
                </button>
            </header>

            {/* Scrollable Message List */}
            <div className="messages-container">
                {isFetchingHistory ? (
                    <div className="flex h-full items-center justify-center">
                        <Loader2 className="animate-spin text-accent-color opacity-50" size={32} />
                    </div>
                ) : (
                    <>
                        {messages.map((msg) => (
                            <MessageItem key={msg.id} message={msg} />
                        ))}

                        {loading && (
                            <div className="message-wrapper assistant">
                                <div className="flex flex-col max-w-[85%]">
                                    <span className="text-xs text-text-secondary mb-1 ml-1 font-medium">ComplianceGPT</span>
                                    <div className="bg-bg-secondary border border-border-color rounded-lg rounded-bl-none p-4 flex items-center gap-2">
                                        <Loader2 size={16} className="spinner text-accent-color" />
                                        <span className="text-text-secondary font-medium whitespace-nowrap">Gathering evidence...</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="mx-auto flex max-w-lg items-center gap-2 rounded-md bg-red-950/40 border border-error-color/50 px-4 py-3 text-sm text-error-color mt-4">
                                <AlertCircle size={16} />
                                <p>{error}</p>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            {/* Input Area */}
            <div className="input-area-container">
                <div className="input-area-content">
                    <div className="framework-selector-container">
                        <div className="framework-selector-header tooltip-trigger">
                            <span className="text-xs text-text-secondary font-medium">Frameworks Scope</span>
                            <Info size={12} className="text-text-secondary" />
                            <div className="tooltip">Toggle frameworks to restrict search context.</div>
                        </div>
                        <div className="framework-chips">
                            {FRAMEWORK_OPTIONS.map((fw) => {
                                const isSelected = selectedFrameworks.has(fw.id);
                                return (
                                    <button
                                        key={fw.id}
                                        className={`framework-chip ${isSelected ? 'selected' : ''}`}
                                        onClick={() => {
                                            const next = new Set(selectedFrameworks);
                                            if (next.has(fw.id)) {
                                                next.delete(fw.id);
                                            } else {
                                                next.add(fw.id);
                                            }
                                            setSelectedFrameworks(next);
                                        }}
                                        disabled={loading}
                                    >
                                        {fw.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="scope-indicator">
                        Searching: {selectedFrameworks.size === 0
                            ? 'None (Please select at least one framework)'
                            : Array.from(selectedFrameworks).map(id => FRAMEWORK_OPTIONS.find(f => f.id === id)?.label).join(', ')}
                    </div>

                    <div className={`input-form ${loading ? 'opacity-70' : ''}`}>
                        <textarea
                            ref={inputRef}
                            className="chat-input"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a compliance question..."
                            rows={1}
                            disabled={loading}
                        />
                        <button
                            type="button"
                            onClick={handleSend}
                            disabled={!input.trim() || loading || isFetchingHistory || selectedFrameworks.size === 0}
                            className="send-button"
                            aria-label="Send message"
                        >
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            </div>
            {/* Report Generation Modal */}
            <ReportModal
                isOpen={isReportModalOpen}
                onClose={() => setIsReportModalOpen(false)}
                messages={messages}
            />
        </main>
    );
}
