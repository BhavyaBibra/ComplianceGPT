import { useState } from 'react';
import { X, FileText, Download, Copy, Loader2, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMessage, generateReport } from '../lib/api';

type ModalState = 'closed' | 'selecting' | 'generating' | 'preview';

interface ReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    messages: ChatMessage[];
}

export function ReportModal({ isOpen, onClose, messages }: ReportModalProps) {
    const [modalState, setModalState] = useState<ModalState>('selecting');
    const [reportType, setReportType] = useState<string>('summary');
    const [reportContent, setReportContent] = useState<string>('');
    const [copied, setCopied] = useState(false);

    if (!isOpen) return null;

    // Reset state on close
    const handleClose = () => {
        setModalState('selecting');
        setReportContent('');
        onClose();
    };

    const handleGenerate = async () => {
        if (messages.length === 0) return;

        setModalState('generating');
        try {
            const result = await generateReport(reportType, messages);
            setReportContent(result.markdown);
            setModalState('preview');
        } catch (error) {
            console.error("Failed to generate report:", error);
            setModalState('selecting'); // Revert on error
            alert("Failed to generate report. Please try again.");
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(reportContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownload = () => {
        const element = document.createElement("a");
        const file = new Blob([reportContent], { type: 'text/markdown' });
        element.href = URL.createObjectURL(file);

        const date = new Date().toISOString().split('T')[0];
        element.download = `ComplianceGPT_${reportType.charAt(0).toUpperCase() + reportType.slice(1)}_Report_${date}.md`;

        document.body.appendChild(element); // Required for this to work in FireFox
        element.click();
        document.body.removeChild(element);
    };

    return (
        <div className="report-modal-overlay">
            <div className={`report-modal-content ${modalState === 'preview' ? 'preview-mode' : ''}`}>

                <div className="report-modal-header">
                    <div className="report-modal-header-title">
                        <FileText size={20} className="text-accent-color" />
                        <h2>
                            {modalState === 'preview' ? 'Report Preview' : 'Generate Compliance Report'}
                        </h2>
                    </div>
                    <button onClick={handleClose} className="report-modal-close">
                        <X size={20} />
                    </button>
                </div>

                <div className="report-modal-body">
                    {modalState === 'selecting' && (
                        <>
                            <p className="report-description">
                                Synthesize your current conversation history into a structured executive Markdown document.
                            </p>

                            <label className="report-form-group">
                                <span className="report-form-label">Report Focus</span>
                                <select
                                    className="report-select"
                                    value={reportType}
                                    onChange={(e) => setReportType(e.target.value)}
                                >
                                    <option value="summary">Executive Summary Report (Default)</option>
                                    <option value="mapping">Cross-Framework Gap Mapping Report</option>
                                    <option value="incident">Mitre ATT&CK Threat Incident Report</option>
                                </select>
                            </label>

                            <div className="report-actions">
                                <button className="report-btn-secondary" onClick={handleClose}>
                                    Cancel
                                </button>
                                <button
                                    className="report-btn-primary"
                                    onClick={handleGenerate}
                                    disabled={messages.length === 0}
                                    title={messages.length === 0 ? "Chat history is empty" : ""}
                                >
                                    Generate Report
                                </button>
                            </div>
                        </>
                    )}

                    {modalState === 'generating' && (
                        <div className="report-generating">
                            <Loader2 size={32} className="text-accent-color spinner" />
                            <p className="report-description">Synthesizing compliance intelligence...</p>
                        </div>
                    )}

                    {modalState === 'preview' && (
                        <>
                            <div className="report-preview-container markdown-body">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {reportContent}
                                </ReactMarkdown>
                            </div>

                            <div className="report-actions-bar">
                                <div className="report-success-msg">
                                    <Check size={14} className="text-success-color" />
                                    Report generation successful
                                </div>
                                <div className="report-actions">
                                    <button className="report-btn-secondary" onClick={handleCopy}>
                                        {copied ? <Check size={16} /> : <Copy size={16} />}
                                        {copied ? 'Copied!' : 'Copy MD'}
                                    </button>
                                    <button className="report-btn-primary" onClick={handleDownload}>
                                        <Download size={16} />
                                        Download (.md)
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
