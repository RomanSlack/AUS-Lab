import { useState, useRef, useEffect } from 'react';

interface ResponseState {
  type: 'thinking' | 'success' | 'error';
  mission?: string;
  message?: string;
}

const AGENTIC_API_URL = 'http://localhost:8001';

export function ChatPill() {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<ResponseState | null>(null);
  const [isFading, setIsFading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fadeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clear any existing fade timeout
  const clearFadeTimeout = () => {
    if (fadeTimeoutRef.current) {
      clearTimeout(fadeTimeoutRef.current);
      fadeTimeoutRef.current = null;
    }
  };

  // Auto-fade response after delay
  useEffect(() => {
    if (response && response.type !== 'thinking') {
      clearFadeTimeout();
      fadeTimeoutRef.current = setTimeout(() => {
        setIsFading(true);
        setTimeout(() => {
          setResponse(null);
          setIsFading(false);
        }, 300);
      }, 4000);
    }

    return () => clearFadeTimeout();
  }, [response]);

  const sendCommand = async () => {
    if (!input.trim() || isLoading) return;

    const command = input.trim();
    setInput('');
    setIsLoading(true);
    setIsFading(false);
    clearFadeTimeout();

    // Show thinking state
    setResponse({ type: 'thinking' });

    try {
      const res = await fetch(`${AGENTIC_API_URL}/command`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const result = await res.json();

      if (result.success) {
        const actions = result.execution_result?.successful_actions || 0;
        const total = result.execution_result?.total_actions || 0;
        setResponse({
          type: 'success',
          mission: result.mission_plan?.mission_name || 'Command executed',
          message: `${actions}/${total} actions completed`,
        });
      } else {
        setResponse({
          type: 'error',
          message: result.error || 'Command failed',
        });
      }
    } catch (err) {
      setResponse({
        type: 'error',
        message: err instanceof Error ? err.message : 'Connection failed',
      });
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendCommand();
    }
  };

  return (
    <div className="command-input-container">
      {response && (
        <div className={`command-response-pill ${isFading ? 'fading' : ''}`}>
          {response.type === 'thinking' ? (
            <div className="response-thinking">
              <div className="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span>Processing command...</span>
            </div>
          ) : (
            <div className={`response-content ${response.type}`}>
              {response.type === 'success' && (
                <>
                  <div className="response-mission">{response.mission}</div>
                  <div className="response-details">{response.message}</div>
                </>
              )}
              {response.type === 'error' && (
                <div>{response.message}</div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="command-input-pill">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter drone command..."
          disabled={isLoading}
        />
        <button onClick={sendCommand} disabled={isLoading || !input.trim()}>
          Execute
        </button>
      </div>
    </div>
  );
}
