import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught an error:', error, info);
    this.setState({ info });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center app-shell">
          <div className="max-w-2xl p-6 panel border border-rose-400/30 bg-rose-500/10">
            <h2 className="text-xl font-semibold text-rose-200">Something went wrong</h2>
            <p className="mt-2 text-sm text-rose-200">{this.state.error?.message || 'Unknown error'}</p>
            <details className="mt-4 text-xs text-slate-500 whitespace-pre-wrap">
              {this.state.info?.componentStack}
            </details>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;