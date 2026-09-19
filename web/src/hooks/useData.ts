import { useEffect, useState } from "react";

interface DataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useData<T>(path: string): DataState<T> {
  const [state, setState] = useState<DataState<T>>({ data: null, loading: true, error: null });

  useEffect(() => {
    let active = true;

    fetch(path)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Could not load ${path} (${response.status})`);
        }
        return response.json() as Promise<T>;
      })
      .then((data) => {
        if (active) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : "The data file could not be loaded.";
          setState({ data: null, loading: false, error: message });
        }
      });

    return () => {
      active = false;
    };
  }, [path]);

  return state;
}
