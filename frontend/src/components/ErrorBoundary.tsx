import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

export interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode | ((error: Error, resetErrorBoundary: () => void) => ReactNode)
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in React component tree:', error, errorInfo)
    this.setState({ errorInfo })
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error || new Error('Unknown error'), this.handleReset)
      }
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-[300px] flex items-center justify-center p-6 w-full">
          <div className="bg-white border border-red-200 rounded-xl shadow-lg max-w-2xl w-full p-6 text-gray-800">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-red-100 text-red-600 rounded-full flex-shrink-0">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-red-700 mb-1">
                  Rendering Error Encountered
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  An unexpected error occurred while rendering this component. The rest of the application remains functional.
                </p>

                {this.state.error && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4 text-xs font-mono text-red-800 overflow-x-auto">
                    <strong>Error:</strong> {this.state.error.message || String(this.state.error)}
                  </div>
                )}

                {this.state.errorInfo?.componentStack && (
                  <details className="mb-4 text-xs text-gray-500">
                    <summary className="cursor-pointer font-medium hover:text-gray-700">
                      Component Stack Trace
                    </summary>
                    <pre className="mt-2 bg-gray-50 p-2 rounded border overflow-x-auto font-mono text-[11px] text-gray-700">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={this.handleReset}
                    className="flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
                  >
                    <RotateCcw className="h-4 w-4" /> Try Again
                  </button>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-md transition-colors"
                  >
                    Reload Page
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
