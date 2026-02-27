import { useEffect, useState } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut } from 'lucide-react';

mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif',
});

interface MermaidDiagramProps {
    chart: string;
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
    const [svgContent, setSvgContent] = useState<string>('');
    const [scale, setScale] = useState(1);
    const [error, setError] = useState<boolean>(false);

    useEffect(() => {
        let isMounted = true;
        const renderDiagram = async () => {
            try {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, chart);
                if (isMounted) {
                    setSvgContent(svg);
                    setError(false);
                }
            } catch (err) {
                console.error("Mermaid parsing failed", err);
                if (isMounted) {
                    setError(true);
                }
            }
        };
        renderDiagram();
        return () => { isMounted = false; };
    }, [chart]);

    const handleZoomIn = () => setScale(prev => Math.min(prev + 0.2, 3));
    const handleZoomOut = () => setScale(prev => Math.max(prev - 0.2, 0.4));
    const handleReset = () => setScale(1);

    if (error) {
        return (
            <div className="p-4 border border-error-color/50 bg-red-950/20 text-error-color text-sm rounded-md my-4">
                Failed to render diagram. Syntax might be invalid.
                <pre className="mt-2 text-xs overflow-x-auto p-2 bg-black/30 rounded text-text-secondary">{chart}</pre>
            </div>
        );
    }

    return (
        <div className="my-4 border border-border-color rounded-lg overflow-hidden flex flex-col bg-[#ffffff] shadow-sm">
            {/* Toolbar */}
            <div className="flex items-center justify-end gap-2 p-2 bg-[#f8f9fa] border-b border-border-color/20 text-[#333]">
                <button onClick={handleZoomOut} className="p-1.5 rounded hover:bg-black/5 transition-colors flex items-center justify-center" title="Zoom Out">
                    <ZoomOut size={16} />
                </button>
                <button onClick={handleReset} className="px-2 focus:outline-none rounded hover:bg-black/5 transition-colors text-xs font-semibold tabular-nums" title="Reset Zoom">
                    {Math.round(scale * 100)}%
                </button>
                <button onClick={handleZoomIn} className="p-1.5 rounded hover:bg-black/5 transition-colors flex items-center justify-center" title="Zoom In">
                    <ZoomIn size={16} />
                </button>
            </div>

            {/* Scrollable container with isolated background for diagram visibility */}
            <div className="overflow-auto w-full flex justify-center p-8 min-h-[250px] items-center relative">
                {!svgContent ? (
                    <div className="animate-pulse flex items-center gap-2 text-[#666] text-sm">
                        <div className="w-4 h-4 border-2 border-[#666] border-t-transparent rounded-full animate-spin"></div>
                        Rendering Diagram...
                    </div>
                ) : (
                    <div
                        dangerouslySetInnerHTML={{ __html: svgContent }}
                        style={{ transform: `scale(${scale})`, transformOrigin: 'top center', transition: 'transform 0.2s ease' }}
                        className="mermaid-content w-full h-full flex justify-center items-center"
                    />
                )}
            </div>
        </div>
    );
}
