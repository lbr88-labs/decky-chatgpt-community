export type PageState = {
  cursor: string | null;
  previous: Array<string | null>;
};

export function firstPage(): PageState;
export function nextPage(state: PageState, nextCursor: string | null): PageState;
export function previousPage(state: PageState): PageState;
export function refreshPage(): PageState;
