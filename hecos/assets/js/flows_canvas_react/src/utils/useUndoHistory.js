import { useRef, useCallback, useReducer } from 'react';

const MAX_HISTORY = 50;

/**
 * useUndoHistory
 * ==============
 * Manages a history stack of { nodes, edges } snapshots.
 * Usage:
 *   const { pushHistory, undo, redo, canUndo, canRedo } = useUndoHistory();
 */
export function useUndoHistory() {
  const historyRef = useRef([]);   // Array of { nodes, edges } snapshots
  const pointerRef = useRef(-1);   // Current position in history (-1 = empty)
  const [tick, forceUpdate] = useReducer(x => x + 1, 0); // Forces re-render to update canUndo/canRedo

  /**
   * Saves a snapshot into the history stack.
   * Trims any "future" states if we branched from an earlier point.
   */
  const pushHistory = useCallback((nodes, edges) => {
    // Trim future branch
    historyRef.current = historyRef.current.slice(0, pointerRef.current + 1);

    // Deep clone via JSON to avoid reference sharing
    const snapshot = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
    };

    historyRef.current.push(snapshot);

    // Enforce max size (trim oldest)
    if (historyRef.current.length > MAX_HISTORY) {
      historyRef.current.shift();
      // pointer stays at end
    } else {
      pointerRef.current++;
    }

    forceUpdate();
  }, []);

  /**
   * Moves back one step in history.
   * Returns the previous { nodes, edges } snapshot, or null if none.
   */
  const undo = useCallback(() => {
    if (pointerRef.current <= 0) return null;
    pointerRef.current--;
    forceUpdate();
    return historyRef.current[pointerRef.current];
  }, []);

  /**
   * Moves forward one step in history.
   * Returns the next { nodes, edges } snapshot, or null if none.
   */
  const redo = useCallback(() => {
    if (pointerRef.current >= historyRef.current.length - 1) return null;
    pointerRef.current++;
    forceUpdate();
    return historyRef.current[pointerRef.current];
  }, []);

  const canUndo = pointerRef.current > 0;
  const canRedo = pointerRef.current < historyRef.current.length - 1;
  const historySize = historyRef.current.length;

  return { pushHistory, undo, redo, canUndo, canRedo, historySize, tick };
}
