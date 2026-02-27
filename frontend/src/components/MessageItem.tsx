import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, Network, ArrowRight, ShieldAlert } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage, RetrievedChunk } from '../lib/api';

interface EvidencePanelProps {
    chunks: RetrievedChunk[];
}

function EvidencePanel({ chunks }: EvidencePanelProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!chunks || chunks.length === 0) return null;

    // Group chunks by framework
    const groupedChunks = chunks.reduce((acc, chunk) => {
        const fw = chunk.framework || 'Unknown';
        if (!acc[fw]) {
            acc[fw] = [];
        }
        acc[fw].push(chunk);
        return acc;
    }, {} as Record<string, RetrievedChunk[]>);

    return (
        <div className="mt-2 text-left">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="evidence-toggle"
            >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <FileText size={14} />
                View Evidence ({chunks.length} chunks)
            </button>

            {isExpanded && (
                <div className="evidence-panel">
                    {Object.entries(groupedChunks).map(([framework, fwChunks]) => (
                        <div key={framework} className="evidence-group">
                            <h4 className="evidence-group-title">{framework.toUpperCase()}</h4>
                            <div className="evidence-group-cards">
                                {fwChunks.map((chunk, idx) => (
                                    <div key={`${framework}-${idx}`} className="evidence-card">
                                        <div className="evidence-header">
                                            <span className="evidence-similarity">
                                                Similarity: {(chunk.similarity * 100).toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="evidence-text">
                                            {chunk.chunk}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function MappingVisualizer({ chunks, answer }: { chunks: RetrievedChunk[], answer: string }) {
    if (!chunks || chunks.length === 0) {
        return (
            <div className="mapping-mode-container">
                <div className="mapping-banner">
                    <Network size={16} className="text-accent-color" />
                    <span>Cross-Framework Control Mapping</span>
                </div>
                <div className="mapping-explanation mt-4 markdown-body bg-transparent">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {answer}
                    </ReactMarkdown>
                </div>
            </div>
        );
    }

    // Assume the first chunk returned is the primary source control (backend structured)
    const sourceFramework = chunks[0].framework || 'Unknown';
    const sourceChunks = chunks.filter(c => c.framework === sourceFramework);
    const targetChunks = chunks.filter(c => c.framework !== sourceFramework);

    // Group target chunks by framework
    const groupedTargets = targetChunks.reduce((acc, chunk) => {
        const fw = chunk.framework || 'Unknown';
        if (!acc[fw]) acc[fw] = [];
        acc[fw].push(chunk);
        return acc;
    }, {} as Record<string, RetrievedChunk[]>);

    return (
        <div className="mapping-mode-container">
            <div className="mapping-banner">
                <Network size={16} className="text-accent-color" />
                <span>Cross-Framework Control Mapping</span>
            </div>

            <div className="mapping-layout">
                {/* Source Column */}
                <div className="mapping-column source-column">
                    <h4 className="mapping-column-title">SOURCE: {sourceFramework.toUpperCase()}</h4>
                    {sourceChunks.map((chunk, idx) => (
                        <div key={`source-${idx}`} className="mapping-card source-card">
                            <div className="mapping-card-header">
                                <span className="mapping-similarity">Similarity: {(chunk.similarity * 100).toFixed(1)}%</span>
                            </div>
                            <div className="mapping-card-text">{chunk.chunk}</div>
                        </div>
                    ))}
                </div>

                {/* Arrow Divider */}
                <div className="mapping-divider">
                    <ArrowRight size={24} className="mapping-arrow" />
                </div>

                {/* Target Column(s) */}
                <div className="mapping-column target-column">
                    {Object.keys(groupedTargets).length > 0 ? (
                        Object.entries(groupedTargets).map(([fw, fwChunks]) => (
                            <div key={fw} className="mapping-target-group">
                                <h4 className="mapping-column-title">TARGET: {fw.toUpperCase()}</h4>
                                {fwChunks.map((chunk, idx) => (
                                    <div key={`target-${fw}-${idx}`} className="mapping-card target-card">
                                        <div className="mapping-card-header">
                                            <span className="mapping-similarity">Similarity: {(chunk.similarity * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="mapping-card-text">{chunk.chunk}</div>
                                    </div>
                                ))}
                            </div>
                        ))
                    ) : (
                        <div className="mapping-no-targets">No target mappings found.</div>
                    )}
                </div>
            </div>

            {/* Assistant Explanation */}
            <div className="mapping-explanation mt-4 markdown-body bg-transparent">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {answer}
                </ReactMarkdown>
            </div>
        </div>
    );
}

function IncidentVisualizer({ chunks, answer }: { chunks: RetrievedChunk[], answer: string }) {
    if (!chunks || chunks.length === 0) {
        return (
            <div className="mapping-mode-container">
                <div className="incident-banner">
                    <ShieldAlert size={16} className="text-error-color" />
                    <span>Incident Response & Threat Mitigation</span>
                </div>
                <div className="mapping-explanation mt-4 border-l-4 border-l-accent-color pl-4">
                    <div className="whitespace-pre-wrap">{answer}</div>
                </div>
            </div>
        );
    }

    // Identify MITRE threat chunk
    const mitreChunks = chunks.filter(c => c.framework === 'mitre');
    const controlChunks = chunks.filter(c => c.framework !== 'mitre');

    // Group defensive control chunks by framework
    const groupedControls = controlChunks.reduce((acc, chunk) => {
        const fw = chunk.framework || 'Unknown';
        if (!acc[fw]) acc[fw] = [];
        acc[fw].push(chunk);
        return acc;
    }, {} as Record<string, RetrievedChunk[]>);

    return (
        <div className="mapping-mode-container">
            <div className="incident-banner">
                <ShieldAlert size={16} className="text-error-color" />
                <span>Incident Response & Threat Mitigation</span>
            </div>

            <div className="mapping-layout">
                {/* Threat Column (Left) */}
                <div className="mapping-column source-column">
                    <h4 className="mapping-column-title">THREAT INTEL: MITRE ATT&CK</h4>
                    {mitreChunks.length > 0 ? (
                        mitreChunks.map((chunk, idx) => (
                            <div key={`threat-${idx}`} className="mapping-card threat-card">
                                <div className="mapping-card-header">
                                    <span className="mapping-similarity text-error-color">Similarity: {(chunk.similarity * 100).toFixed(1)}%</span>
                                </div>
                                <div className="mapping-card-text">{chunk.chunk}</div>
                            </div>
                        ))
                    ) : (
                        <div className="mapping-no-targets flex items-center justify-center p-4">No specific MITRE intel referenced.</div>
                    )}
                </div>

                {/* Arrow Divider */}
                <div className="mapping-divider">
                    <ArrowRight size={24} className="mapping-arrow text-success-color" />
                </div>

                {/* Defense Column(s) (Right) */}
                <div className="mapping-column target-column">
                    {Object.keys(groupedControls).length > 0 ? (
                        Object.entries(groupedControls).map(([fw, fwChunks]) => (
                            <div key={fw} className="mapping-target-group">
                                <h4 className="mapping-column-title">DEFENSIVE CONTROLS: {fw.toUpperCase()}</h4>
                                {fwChunks.map((chunk, idx) => (
                                    <div key={`defense-${fw}-${idx}`} className="mapping-card defense-card">
                                        <div className="mapping-card-header">
                                            <span className="mapping-similarity text-success-color">Defense Match: {(chunk.similarity * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="mapping-card-text">{chunk.chunk}</div>
                                    </div>
                                ))}
                            </div>
                        ))
                    ) : (
                        <div className="mapping-no-targets">No defensive controls found.</div>
                    )}
                </div>
            </div>

            {/* Assistant Explanation */}
            <div className="mapping-explanation border-l-4 border-l-accent-color pl-4 mt-4 markdown-body bg-transparent">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {answer}
                </ReactMarkdown>
            </div>
        </div>
    );
}

interface MessageItemProps {
    message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
    const isUser = message.role === 'user';
    const isMapping = !!message.mapping_mode && !isUser;
    const isIncident = !!message.incident_mode && !isUser;

    return (
        <div className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}>
            <div className="flex flex-col max-w-[85%]">
                {!isUser && <span className="text-xs text-text-secondary mb-1 ml-1 font-medium">ComplianceGPT</span>}

                {isMapping ? (
                    <div className="bg-bg-secondary border border-border-color rounded-lg rounded-bl-none p-5">
                        <MappingVisualizer chunks={message.evidence || []} answer={message.content} />
                    </div>
                ) : isIncident ? (
                    <div className="bg-bg-secondary border border-border-color rounded-lg rounded-bl-none p-5">
                        <IncidentVisualizer chunks={message.evidence || []} answer={message.content} />
                    </div>
                ) : (
                    <div className={`p-4 rounded-lg text-[0.95rem] leading-[1.6] ${!isUser ? 'markdown-body' : ''} ${isUser
                        ? 'bg-accent-color text-white rounded-br-none'
                        : 'bg-bg-secondary border border-border-color rounded-bl-none'
                        }`}>
                        {!isUser ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {message.content}
                            </ReactMarkdown>
                        ) : (
                            <div className="whitespace-pre-wrap">{message.content}</div>
                        )}
                    </div>
                )}

                {/* Citation Badges */}
                {message.citations && message.citations.length > 0 && (
                    <div className="citation-badges">
                        {message.citations.map((cite) => (
                            <span key={cite} className="badge">
                                {cite}
                            </span>
                        ))}
                    </div>
                )}

                {/* Evidence Panel (if chunks available) */}
                {message.evidence && message.evidence.length > 0 && (
                    <EvidencePanel chunks={message.evidence} />
                )}
            </div>
        </div>
    );
}
