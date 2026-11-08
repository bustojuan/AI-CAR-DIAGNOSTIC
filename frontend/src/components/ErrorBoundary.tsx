import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="fatal-error">
          <h1>This view could not be displayed.</h1>
          <p>
            The received information may be incomplete. This view does not
            provide a repair recommendation.{" "}
          </p>
          <button
            className="button primary"
            onClick={() => window.location.reload()}
          >
            Reload{" "}
          </button>
        </main>
      );
    return this.props.children;
  }
}
