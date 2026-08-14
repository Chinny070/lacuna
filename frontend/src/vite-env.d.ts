/// <reference types="vite/client" />

interface Window {
  ethereum?: {
    request: (args: { method: string; params?: unknown[] | object }) => Promise<unknown>;
    on: (event: "accountsChanged" | "chainChanged" | "disconnect", listener: (...args: unknown[]) => void) => void;
    removeListener: (event: "accountsChanged" | "chainChanged" | "disconnect", listener: (...args: unknown[]) => void) => void;
  };
}
