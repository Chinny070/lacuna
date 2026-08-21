import { useState } from "react";

/**
 * Record IDs are contract-generated and needed as input to later lifecycle
 * calls, so they must be readable and copyable wherever they appear -- not
 * transcribed by eye from a hash.
 */
export function CopyId({ id, label }: { id: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  if (!id || id === "—") return null;
  const copy = async (event: React.MouseEvent) => {
    // Cards are links; copying must not navigate away from the list.
    event.preventDefault();
    event.stopPropagation();
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <span className="copy-id">
      {label && <span className="copy-id-label">{label}</span>}
      <code>{id}</code>
      <button type="button" className="copy-id-button" onClick={(event) => void copy(event)}>
        {copied ? "Copied" : "Copy"}
      </button>
    </span>
  );
}
