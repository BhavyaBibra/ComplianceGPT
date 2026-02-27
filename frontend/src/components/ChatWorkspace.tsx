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

const SUGGESTION_CARDS = [
    { icon: '🔗', title: 'Map Controls', prompt: 'Map NIST 800-53 AC-2 to its ISO 27001 equivalent controls' },
    { icon: '🛡️', title: 'Analyze Incident', prompt: 'A phishing email compromised an admin account. What controls should we review?' },
    { icon: '📋', title: 'Explain Controls', prompt: 'Explain the NIST 800-53 access control family and its key controls' },
    { icon: '📊', title: 'Compliance Gap', prompt: 'What are common gaps between ISO 27001 and NIST CSF implementations?' },
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
    const [isWelcome, setIsWelcome] = useState(true);

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

    // Ref to skip fetching when we just created a new conversation (messages are already in state)
    const justCreatedRef = useRef(false);

    useEffect(() => {
        if (!activeId) {
            setMessages([]);
            setIsWelcome(true);
            return;
        }

        // If we just created this conversation via handleSend, skip the fetch
        // because messages are already in the local state from the stream.
        if (justCreatedRef.current) {
            justCreatedRef.current = false;
            setIsWelcome(false);
            return;
        }

        // User clicked an existing sidebar conversation — fetch its history
        setIsWelcome(false);
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

    const handleSend = async (overrideInput?: string) => {
        const text = (overrideInput || input).trim();
        if (!text || loading || isFetchingHistory) return;

        setIsWelcome(false);

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
        };

        const assistantMsgId = (Date.now() + 1).toString();
        const assistantCreated = { current: false };

        // Only add the user message now; assistant message is created when first token arrives
        setMessages((prev) => [...prev, userMsg]);

        setInput('');
        setLoading(true);
        setError(null);

        try {
            const frameworksArr = Array.from(selectedFrameworks);

            await submitQueryStream(text, frameworksArr, activeId, {
                onMetadata: (data) => {
                    setMessages((prev) => {
                        // If assistant message hasn't been created yet, create it with metadata
                        if (!assistantCreated.current) {
                            assistantCreated.current = true;
                            return [...prev, {
                                id: assistantMsgId,
                                role: 'assistant' as const,
                                content: '',
                                citations: data.citations,
                                frameworks_used: data.frameworks_used,
                                evidence: data.retrieved_chunks,
                                mapping_mode: data.mapping_mode,
                                incident_mode: data.incident_mode
                            }];
                        }
                        return prev.map(msg =>
                            msg.id === assistantMsgId ? {
                                ...msg,
                                citations: data.citations,
                                frameworks_used: data.frameworks_used,
                                evidence: data.retrieved_chunks,
                                mapping_mode: data.mapping_mode,
                                incident_mode: data.incident_mode
                            } : msg
                        );
                    });
                    setLoading(false);
                },
                onToken: (token) => {
                    setMessages((prev) => {
                        // If assistant message hasn't been created yet, create it with the first token
                        if (!assistantCreated.current) {
                            assistantCreated.current = true;
                            return [...prev, {
                                id: assistantMsgId,
                                role: 'assistant' as const,
                                content: token
                            }];
                        }
                        return prev.map(msg =>
                            msg.id === assistantMsgId ? { ...msg, content: msg.content + token } : msg
                        );
                    });
                },
                onConversationId: (id) => {
                    justCreatedRef.current = true;
                    onNewConversation(id);
                },
                onError: (err) => {
                    console.error(err);
                    setError(err.message || 'Streaming failed.');
                    setLoading(false);
                },
                onComplete: () => {
                    setLoading(false);
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

    const handleSuggestionClick = (prompt: string) => {
        setInput(prompt);
        handleSend(prompt);
    };

    return (
        <main className="chat-workspace">
            <header className="chat-header">
                <div className="header-title-container">
                    <Shield size={24} className="header-shield-icon" />
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

            <div className="messages-container">
                {isFetchingHistory ? (
                    <div className="loading-center">
                        <Loader2 className="loading-spinner" size={32} />
                    </div>
                ) : isWelcome ? (
                    /* ======= Welcome Screen ======= */
                    <div className="welcome-screen">
                        <div className="welcome-icon-wrapper">
                            <Shield size={48} className="welcome-shield" />
                        </div>
                        <h2 className="welcome-heading">How can I help you today?</h2>
                        <p className="welcome-subtext">
                            Ask about compliance frameworks, map controls across standards, or analyze security incidents.
                        </p>
                        <div className="suggestion-cards-grid">
                            {SUGGESTION_CARDS.map((card, idx) => (
                                <button
                                    key={idx}
                                    className="suggestion-card"
                                    onClick={() => handleSuggestionClick(card.prompt)}
                                >
                                    <span className="suggestion-card-icon">{card.icon}</span>
                                    <span className="suggestion-card-title">{card.title}</span>
                                    <span className="suggestion-card-prompt">{card.prompt}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((msg) => (
                            <MessageItem key={msg.id} message={msg} />
                        ))}

                        {loading && (
                            <div className="message-wrapper assistant">
                                <div className="assistant-message-content">
                                    <div className="typing-indicator-wrapper">
                                        <div className="typing-indicator">
                                            <span className="typing-dot"></span>
                                            <span className="typing-dot"></span>
                                            <span className="typing-dot"></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="error-banner">
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
                        <div className="framework-selector-header">
                            <span className="framework-label">Frameworks Scope</span>
                            <div className="tooltip-trigger">
                                <Info size={12} className="framework-info-icon" />
                                <div className="tooltip">Toggle frameworks to restrict search context.</div>
                            </div>
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

                    <div className={`input-form ${loading ? 'input-form-disabled' : ''}`}>
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
                            onClick={() => handleSend()}
                            disabled={!input.trim() || loading || isFetchingHistory || selectedFrameworks.size === 0}
                            className="send-button"
                            aria-label="Send message"
                        >
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            </div>
            <ReportModal
                isOpen={isReportModalOpen}
                onClose={() => setIsReportModalOpen(false)}
                messages={messages}
            />
        </main>
    );
}
