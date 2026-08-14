import { useCallback, useEffect, useState } from "react";
import { normalizeGenLayerError, type NormalizedError } from "../lib/genlayer/errors";

export function useContractData<T>(load: () => Promise<T>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<NormalizedError>();
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true); setError(undefined);
    try { setData(await load()); } catch (cause) { setError(normalizeGenLayerError(cause)); } finally { setLoading(false); }
  // load is intentionally supplied by page closures; dependencies define refresh triggers.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);
  useEffect(() => { void refresh(); }, [refresh]);
  return { data, error, loading, refresh };
}
