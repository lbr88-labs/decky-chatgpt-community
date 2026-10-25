export function firstPage() {
  return { cursor: null, previous: [] };
}

export function nextPage(state, nextCursor) {
  if (nextCursor == null) return state;
  return { cursor: nextCursor, previous: [...state.previous, state.cursor] };
}

export function previousPage(state) {
  if (state.previous.length === 0) return state;
  const previous = state.previous.slice(0, -1);
  return { cursor: state.previous[state.previous.length - 1], previous };
}

export function refreshPage() {
  return firstPage();
}
