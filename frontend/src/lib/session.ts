/** Front-end session flag (the LinkedIn cookie itself never reaches the browser). */
const ENTERED_KEY = "linkesearch:entered";
const LOGGED_OUT_KEY = "linkesearch:loggedOut";

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

export const session = {
  enter: () =>
    safe(() => {
      sessionStorage.setItem(ENTERED_KEY, "1");
      sessionStorage.removeItem(LOGGED_OUT_KEY);
    }, undefined),
  isEntered: () => safe(() => sessionStorage.getItem(ENTERED_KEY) === "1", false),
  justLoggedOut: () => safe(() => sessionStorage.getItem(LOGGED_OUT_KEY) === "1", false),
  /** Clears every cached value of the app and remembers the explicit logout. */
  logout: () =>
    safe(() => {
      sessionStorage.clear();
      sessionStorage.setItem(LOGGED_OUT_KEY, "1");
    }, undefined),
};
